import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END

from app.tools.mcp_tools import (
    get_location_context,
    search_civic_guidelines,
    find_similar_issues,
    calculate_priority,
    create_issue,
    notify_authority
)
from app.db import get_db_connection

# State schema for LangGraph
class VillageVoiceState(TypedDict):
    report_id: str
    raw_text: str
    original_text: str
    normalized_text: str
    language: str
    image_url: str
    latitude: float
    longitude: float
    ward: str
    
    category: str
    subcategory: str
    severity: str
    duration_days: int
    affected_pop_est: int
    
    rag_sources: List[Dict[str, str]]
    image_analysis: Dict[str, Any]
    
    issue_id: str
    is_new_issue: bool
    affected_reports_count: int
    
    priority_breakdown: Dict[str, Any]
    priority_score: int
    
    confidence: float
    risk_score: float
    needs_human_review: bool
    escalation_reason: str
    routing_decision: str
    
    traces: List[Dict[str, Any]]

# Dictionary of Malayalam translations / keywords for offline robustness
MALAYALAM_KEYWORD_MAP = {
    "വെള്ളം": ("Water Supply", "No water supply reported", "Water Supply"),
    "വെള്ളമില്ല": ("Water Supply", "No water supply for 3 days", "Water Supply"),
    "റോഡ്": ("Roads", "Pothole or road surface damage", "Roads"),
    "കുഴി": ("Roads", "Dangerous pothole on road", "Roads"),
    "മാലിന്യം": ("Waste Management", "Overflowing waste accumulation", "Waste Management"),
    "ചെളി": ("Drainage", "Drainage overflow / blockage", "Drainage"),
    "കറന്റ്": ("Electricity", "Power outage / streetlight damage", "Electricity"),
    "ലൈറ്റ്": ("Streetlight", "Streetlight not working", "Streetlight")
}

# --- AGENT NODES ---

def intake_agent(state: VillageVoiceState) -> VillageVoiceState:
    text = state.get("raw_text", "").strip()
    lang = state.get("language", "en")
    
    # Simple language detection & Malayalam translation normalization
    normalized = text
    detected_lang = "en"
    
    if any("\u0d00" <= char <= "\u0d7f" for char in text):
        detected_lang = "ml"
        # Map Malayalam text to normalized English
        if "വെള്ളമില്ല" in text or "വെള്ളം" in text:
            normalized = "No drinking water supply in our house for three days."
        elif "റോഡ്" in text or "കുഴി" in text:
            normalized = "Large dangerous pothole near school road."
        elif "മാലിന്യം" in text:
            normalized = "Overflowing waste uncollected for one week."
        elif "ലൈറ്റ്" in text or "തെരുവിൽ" in text:
            normalized = "Streetlight damaged dark street corner."
        elif "കറന്റ്" in text:
            normalized = "Power failure in residential lane."
        else:
            normalized = f"Reported issue: {text}"
            
    # Extract duration heuristic
    duration = 1
    if "three days" in normalized.lower() or "3 days" in normalized.lower() or "മൂന്ന്" in text:
        duration = 3
    elif "week" in normalized.lower() or "7 days" in normalized.lower():
        duration = 7
    elif "5 days" in normalized.lower() or "5" in normalized.lower():
        duration = 5
    elif "4 days" in normalized.lower() or "4" in normalized.lower():
        duration = 4

    # Location lookup tool call
    loc_ctx = get_location_context(state["latitude"], state["longitude"])

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Intake Agent",
        "action": "Language Detection & Normalization",
        "input_summary": f"Raw Text: '{text}' ({detected_lang})",
        "output_summary": f"Normalized: '{normalized}' | Ward: {loc_ctx['ward']}",
        "confidence": 0.96,
        "tool_calls": ["get_location_context"],
        "retrieved_sources": [],
        "decision": "Parsed successfully"
    }
    
    state["original_text"] = text if text else "Voice Report"
    state["normalized_text"] = normalized
    state["language"] = detected_lang
    state["duration_days"] = duration
    state["ward"] = loc_ctx["ward"]
    state["traces"].append(trace)
    return state

def classification_agent(state: VillageVoiceState) -> VillageVoiceState:
    norm_text = state["normalized_text"].lower()
    raw_orig = state["original_text"]
    
    if "water" in norm_text or "pipe" in norm_text or "വെള്ളം" in raw_orig:
        category = "Water Supply"
        subcategory = "Pipeline Disruption"
        severity = "High" if state["duration_days"] >= 3 or "school" in norm_text or "burst" in norm_text or "tank" in norm_text else "Medium"
    elif "pothole" in norm_text or "road" in norm_text or "കുഴി" in raw_orig or "റോഡ്" in raw_orig:
        category = "Roads"
        subcategory = "Hazardous Pothole"
        severity = "High" if "school" in norm_text or "bus" in norm_text or "huge" in norm_text or "deep" in norm_text else "Medium"
    elif "waste" in norm_text or "garbage" in norm_text or "trash" in norm_text or "drain" in norm_text or "sewage" in norm_text or "മാലിന്യം" in raw_orig:
        category = "Waste Management"
        subcategory = "Uncollected Trash / Sewage"
        severity = "High" if state["duration_days"] >= 5 or "overflowing" in norm_text or "sewage" in norm_text or "well" in norm_text else "Medium"
    elif "streetlight" in norm_text or " bulb" in norm_text or "ലൈറ്റ്" in raw_orig:
        category = "Streetlight"
        subcategory = "Streetlight Damage"
        severity = "Medium"
    elif "electric" in norm_text or "wire" in norm_text or "കറന്റ്" in raw_orig or "power" in norm_text:
        category = "Electricity"
        subcategory = "Streetlight / Wire Damage"
        severity = "High" if "wire" in norm_text or "fallen" in norm_text else "Medium"
    else:
        category = "Other"
        subcategory = "General Civic Issue"
        severity = "Medium"

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Classification Agent",
        "action": "Taxonomy Classification",
        "input_summary": f"Normalized Text: '{state['normalized_text']}'",
        "output_summary": f"Category: {category} | Severity: {severity}",
        "confidence": 0.94,
        "tool_calls": [],
        "retrieved_sources": [],
        "decision": f"Taxonomy mapped to {category}"
    }
    
    state["category"] = category
    state["subcategory"] = subcategory
    state["severity"] = severity
    state["traces"].append(trace)
    return state

def rag_retriever_agent(state: VillageVoiceState) -> VillageVoiceState:
    sources = search_civic_guidelines(state["normalized_text"], category=state["category"])
    
    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Knowledge Retriever Agent",
        "action": "RAG Vector Lookup",
        "input_summary": f"Query: '{state['category']} - {state['normalized_text']}'",
        "output_summary": f"Retrieved {len(sources)} guideline chunks",
        "confidence": 0.92,
        "tool_calls": ["search_civic_guidelines"],
        "retrieved_sources": [s["title"] for s in sources],
        "decision": f"Grounded in {sources[0]['title'] if sources else 'Default guidelines'}"
    }
    
    state["rag_sources"] = sources
    state["traces"].append(trace)
    return state

def image_agent(state: VillageVoiceState) -> VillageVoiceState:
    img_url = state.get("image_url")
    if not img_url:
        state["image_analysis"] = {"detected_issue": "No image provided", "confidence": 1.0, "safety_risk": 0.1}
        return state

    # Mock Vision AI classification for demo mode
    if "ambiguous" in img_url.lower() or "unclear" in img_url.lower():
        analysis = {"detected_issue": "Ambiguous public structure shadow", "confidence": 0.45, "safety_risk": 0.65}
    elif "water" in img_url.lower() or "tap" in img_url.lower():
        analysis = {"detected_issue": "Dry tap / leaking pipe joint", "confidence": 0.91, "safety_risk": 0.20}
    elif "road" in img_url.lower() or "pothole" in img_url.lower():
        analysis = {"detected_issue": "Deep road surface depression", "confidence": 0.88, "safety_risk": 0.75}
    else:
        analysis = {"detected_issue": "Visible infrastructure defect", "confidence": 0.85, "safety_risk": 0.30}

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Image Analysis Agent",
        "action": "Multimodal Visual Inspection",
        "input_summary": f"Image URL: {img_url}",
        "output_summary": f"Detected: {analysis['detected_issue']} (Confidence: {analysis['confidence']})",
        "confidence": analysis["confidence"],
        "tool_calls": [],
        "retrieved_sources": [],
        "decision": f"Visual Risk Score: {analysis['safety_risk']}"
    }
    
    state["image_analysis"] = analysis
    state["traces"].append(trace)
    return state

def clustering_agent(state: VillageVoiceState) -> VillageVoiceState:
    sim_issues = find_similar_issues(state["category"], state["latitude"], state["longitude"])
    
    if sim_issues:
        matched = sim_issues[0]
        state["issue_id"] = matched["issue_id"]
        state["is_new_issue"] = False
        state["affected_reports_count"] = matched["affected_reports"] + 1
        decision = f"Clustered into existing Community Issue {matched['issue_id']}"
    else:
        state["issue_id"] = f"ISSUE-{uuid.uuid4().hex[:6].upper()}"
        state["is_new_issue"] = True
        state["affected_reports_count"] = 1
        decision = f"Created new Community Issue {state['issue_id']}"

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Issue Clustering Agent",
        "action": "Spatial & Semantic Deduplication",
        "input_summary": f"Category: {state['category']} | Location: ({state['latitude']}, {state['longitude']})",
        "output_summary": f"{decision} (Total reports: {state['affected_reports_count']})",
        "confidence": 0.95,
        "tool_calls": ["find_similar_issues"],
        "retrieved_sources": [],
        "decision": decision
    }
    
    state["traces"].append(trace)
    return state

def priority_agent(state: VillageVoiceState) -> VillageVoiceState:
    safety_risk = state.get("image_analysis", {}).get("safety_risk", 0.2)
    p_breakdown = calculate_priority(
        state["severity"],
        state["duration_days"],
        affected_pop_est=15 if state["affected_reports_count"] > 1 else 3,
        safety_risk=safety_risk,
        num_reports=state["affected_reports_count"]
    )
    
    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Priority Agent",
        "action": "Multi-Factor Priority Scoring",
        "input_summary": f"Sev: {state['severity']} | Dur: {state['duration_days']} days | Reports: {state['affected_reports_count']}",
        "output_summary": f"Calculated Priority Score: {p_breakdown['total_priority']}/100",
        "confidence": 0.96,
        "tool_calls": ["calculate_priority"],
        "retrieved_sources": [],
        "decision": p_breakdown["reasoning"]
    }
    
    state["priority_breakdown"] = p_breakdown
    state["priority_score"] = p_breakdown["total_priority"]
    state["traces"].append(trace)
    return state

def safety_critic_agent(state: VillageVoiceState) -> VillageVoiceState:
    img_conf = state.get("image_analysis", {}).get("confidence", 0.95)
    overall_confidence = round(0.5 * 0.95 + 0.5 * img_conf, 2)
    risk_score = state.get("image_analysis", {}).get("safety_risk", 0.2)
    
    needs_review = False
    reason = None
    
    if overall_confidence < 0.60:
        needs_review = True
        reason = f"Low AI Confidence ({overall_confidence}) — visual evidence is uncertain."
    elif risk_score >= 0.60:
        needs_review = True
        reason = f"High Public Safety Risk ({risk_score}) — immediate human verification required."
    elif state["category"] == "Other":
        needs_review = True
        reason = "Uncategorized civic issue requires manual department review."

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Safety & Confidence Critic",
        "action": "Guardrail Verification & Risk Audit",
        "input_summary": f"Conf: {overall_confidence} | Risk: {risk_score}",
        "output_summary": f"Needs Human Review: {needs_review} ({reason if reason else 'Passed Safety Check'})",
        "confidence": overall_confidence,
        "tool_calls": [],
        "retrieved_sources": [],
        "decision": "Safety critic approved" if not needs_review else f"Escalated: {reason}"
    }
    
    state["confidence"] = overall_confidence
    state["risk_score"] = risk_score
    state["needs_human_review"] = needs_review
    state["escalation_reason"] = reason
    state["traces"].append(trace)
    return state

def router_agent(state: VillageVoiceState) -> VillageVoiceState:
    if state["needs_human_review"]:
        routing = "HUMAN_REVIEW"
    elif state["priority_score"] >= 85:
        routing = "URGENT_ESCALATION"
    else:
        routing = "AUTO_PROCESS"

    state["routing_decision"] = routing

    # Save to SQLite Database
    now = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Save Report
    cursor.execute("""
        INSERT INTO reports (id, issue_id, original_text, normalized_text, language, category, severity, duration_days, confidence, latitude, longitude, ward, image_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        state["report_id"],
        state["issue_id"],
        state["original_text"],
        state["normalized_text"],
        state["language"],
        state["category"],
        state["severity"],
        state["duration_days"],
        state["confidence"],
        state["latitude"],
        state["longitude"],
        state["ward"],
        state.get("image_url"),
        now
    ))
    
    # Department routing mapping
    dept_map = {
        "Water Supply": "Kerala Water Authority (KWA)",
        "Roads": "Public Works Department (PWD)",
        "Waste Management": "Haritha Karma Sena / Panchayat Health Wing",
        "Sanitation": "Panchayat Sanitation Wing",
        "Electricity": "KSEB Electrical Section",
        "Streetlight": "Panchayat Lighting Cell",
        "Drainage": "Panchayat Health Inspection",
        "Other": "Gram Panchayat Executive Officer"
    }
    dept = dept_map.get(state["category"], "Gram Panchayat Executive Officer")

    # Upsert Issue
    if state["is_new_issue"]:
        title = f"{state['category']} - {state['ward']} ({state['normalized_text'][:35]}...)"
        create_issue({
            "id": state["issue_id"],
            "title": title,
            "category": state["category"],
            "subcategory": state["subcategory"],
            "priority_score": state["priority_score"],
            "severity": state["severity"],
            "duration_days": state["duration_days"],
            "affected_reports_count": state["affected_reports_count"],
            "status": "HUMAN_REVIEW" if state["needs_human_review"] else "Reported",
            "assigned_department": dept,
            "latitude": state["latitude"],
            "longitude": state["longitude"],
            "ward": state["ward"],
            "confidence": state["confidence"],
            "risk_score": state["risk_score"],
            "needs_human_review": state["needs_human_review"],
            "escalation_reason": state["escalation_reason"],
            "priority_breakdown": state["priority_breakdown"],
            "rag_sources": state["rag_sources"],
            "image_analysis": state["image_analysis"],
            "created_at": now,
            "updated_at": now
        }, conn=conn)
    else:
        cursor.execute("""
            UPDATE issues SET 
                affected_reports_count = ?, 
                priority_score = ?, 
                updated_at = ? 
            WHERE id = ?
        """, (state["affected_reports_count"], state["priority_score"], now, state["issue_id"]))

    # Save Traces
    for tr in state["traces"]:
        cursor.execute("""
            INSERT INTO traces (report_id, issue_id, timestamp, agent_name, action, input_summary, output_summary, confidence, tool_calls, retrieved_sources, decision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state["report_id"],
            state["issue_id"],
            tr["timestamp"],
            tr["agent_name"],
            tr["action"],
            tr["input_summary"],
            tr["output_summary"],
            tr["confidence"],
            json.dumps(tr["tool_calls"]),
            json.dumps(tr["retrieved_sources"]),
            tr["decision"]
        ))
        
    conn.commit()
    conn.close()

    if routing == "URGENT_ESCALATION":
        notify_authority(state["issue_id"], state["priority_score"], dept)

    trace = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "agent_name": "Router & Escalation Agent",
        "action": "Final Routing Dispatch",
        "input_summary": f"Issue ID: {state['issue_id']} | Priority: {state['priority_score']}",
        "output_summary": f"Routed to {routing} | Assigned Dept: {dept}",
        "confidence": 1.0,
        "tool_calls": ["create_issue", "notify_authority"],
        "retrieved_sources": [],
        "decision": f"Final status set to {routing}"
    }
    state["traces"].append(trace)
    return state

# --- BUILD LANGGRAPH WORKFLOW ---

builder = StateGraph(VillageVoiceState)

builder.add_node("intake", intake_agent)
builder.add_node("classifier", classification_agent)
builder.add_node("retriever", rag_retriever_agent)
builder.add_node("image", image_agent)
builder.add_node("clustering", clustering_agent)
builder.add_node("priority", priority_agent)
builder.add_node("critic", safety_critic_agent)
builder.add_node("router", router_agent)

builder.set_entry_point("intake")
builder.add_edge("intake", "classifier")
builder.add_edge("classifier", "retriever")
builder.add_edge("retriever", "image")
builder.add_edge("image", "clustering")
builder.add_edge("clustering", "priority")
builder.add_edge("priority", "critic")
builder.add_edge("critic", "router")
builder.add_edge("router", END)

village_voice_graph = builder.compile()

def process_resident_report(raw_text: str, language: str = "en", image_url: str = None, latitude: float = 10.0261, longitude: float = 76.3125) -> Dict[str, Any]:
    initial_state = {
        "report_id": f"REP-{uuid.uuid4().hex[:6].upper()}",
        "raw_text": raw_text,
        "original_text": "",
        "normalized_text": "",
        "language": language,
        "image_url": image_url,
        "latitude": latitude,
        "longitude": longitude,
        "ward": "Ward 4",
        "category": "",
        "subcategory": "",
        "severity": "",
        "duration_days": 1,
        "affected_pop_est": 1,
        "rag_sources": [],
        "image_analysis": {},
        "issue_id": "",
        "is_new_issue": True,
        "affected_reports_count": 1,
        "priority_breakdown": {},
        "priority_score": 0,
        "confidence": 1.0,
        "risk_score": 0.0,
        "needs_human_review": False,
        "escalation_reason": "",
        "routing_decision": "",
        "traces": []
    }
    
    final_state = village_voice_graph.invoke(initial_state)
    return final_state
