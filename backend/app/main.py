import json
import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import init_db, get_db_connection
from app.agents.graph import process_resident_report
from app.tools.mcp_tools import update_issue_status, assign_issue, record_feedback
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="Village Voice API",
    description="AI-Powered Rural Community Issue Intelligence Platform API",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def startup_event():
    init_db()

class ReportInput(BaseModel):
    raw_text: Optional[str] = ""
    language: Optional[str] = "en"
    image_url: Optional[str] = None
    latitude: Optional[float] = 10.0261
    longitude: Optional[float] = 76.3125

class StatusUpdateInput(BaseModel):
    status: str

class FeedbackInput(BaseModel):
    issue_id: str
    resolved: bool
    useful_info: bool
    comments: Optional[str] = ""

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Village Voice API is active and healthy", "track": "Track 04 — Sustainability & Smart Infrastructure"}

@app.post("/api/reports")
def create_report(input_data: ReportInput):
    """Processes resident report through multi-agent graph."""
    if not input_data.raw_text and not input_data.image_url:
        raise HTTPException(status_code=400, detail="Report must contain text or image.")
    
    result = process_resident_report(
        raw_text=input_data.raw_text,
        language=input_data.language,
        image_url=input_data.image_url,
        latitude=input_data.latitude,
        longitude=input_data.longitude
    )
    return {
        "status": "SUCCESS",
        "report_id": result["report_id"],
        "issue_id": result["issue_id"],
        "original_text": result["original_text"],
        "normalized_text": result["normalized_text"],
        "category": result["category"],
        "severity": result["severity"],
        "duration_days": result["duration_days"],
        "priority_score": result["priority_score"],
        "confidence": result["confidence"],
        "risk_score": result["risk_score"],
        "needs_human_review": result["needs_human_review"],
        "escalation_reason": result["escalation_reason"],
        "routing_decision": result["routing_decision"],
        "priority_breakdown": result["priority_breakdown"],
        "rag_sources": result["rag_sources"],
        "image_analysis": result["image_analysis"],
        "agent_traces": result["traces"]
    }

@app.get("/api/issues")
def get_issues(
    category: Optional[str] = None,
    status: Optional[str] = None,
    needs_review: Optional[bool] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM issues WHERE 1=1"
    params = []
    
    if category and category != "ALL":
        query += " AND category = ?"
        params.append(category)
    if status and status != "ALL":
        query += " AND status = ?"
        params.append(status)
    if needs_review is not None:
        query += " AND needs_human_review = ?"
        params.append(1 if needs_review else 0)
        
    query += " ORDER BY priority_score DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    issues = []
    for r in rows:
        item = dict(r)
        item["priority_breakdown"] = json.loads(item["priority_breakdown"])
        item["rag_sources"] = json.loads(item["rag_sources"])
        item["image_analysis"] = json.loads(item["image_analysis"]) if item["image_analysis"] else None
        item["needs_human_review"] = bool(item["needs_human_review"])
        issues.append(item)
        
    return {"issues": issues}

@app.get("/api/issues/{issue_id}")
def get_issue_detail(issue_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Issue not found")
        
    issue = dict(row)
    issue["priority_breakdown"] = json.loads(issue["priority_breakdown"])
    issue["rag_sources"] = json.loads(issue["rag_sources"])
    issue["image_analysis"] = json.loads(issue["image_analysis"]) if issue["image_analysis"] else None
    issue["needs_human_review"] = bool(issue["needs_human_review"])

    # Fetch associated reports
    cursor.execute("SELECT * FROM reports WHERE issue_id = ? ORDER BY created_at DESC", (issue_id,))
    reports = [dict(r) for r in cursor.fetchall()]

    # Fetch agent trace logs
    cursor.execute("SELECT * FROM traces WHERE issue_id = ? ORDER BY id ASC", (issue_id,))
    traces = []
    for t in cursor.fetchall():
        tr = dict(t)
        tr["tool_calls"] = json.loads(tr["tool_calls"])
        tr["retrieved_sources"] = json.loads(tr["retrieved_sources"])
        traces.append(tr)

    conn.close()
    return {
        "issue": issue,
        "reports": reports,
        "traces": traces
    }

@app.patch("/api/issues/{issue_id}/status")
def update_status(issue_id: str, payload: StatusUpdateInput):
    update_issue_status(issue_id, payload.status)
    return {"status": "SUCCESS", "issue_id": issue_id, "new_status": payload.status}

@app.post("/api/feedback")
def submit_feedback(payload: FeedbackInput):
    record_feedback(payload.issue_id, payload.resolved, payload.useful_info, payload.comments)
    return {"status": "SUCCESS", "message": "Feedback recorded"}

@app.get("/api/demo-presets")
def get_demo_presets():
    return {
        "presets": [
            {
                "id": "DEMO-1",
                "title": "DEMO 1 — Water Shortage (Malayalam Voice)",
                "raw_text": "മൂന്ന് ദിവസമായി ഞങ്ങളുടെ വീട്ടിൽ വെള്ളമില്ല.",
                "language": "ml",
                "image_url": "https://images.unsplash.com/photo-1541888946425-d0fbb186a5b3?w=500",
                "latitude": 10.0261,
                "longitude": 76.3125,
                "expected": "Water Supply | High Priority | 3 days | Malayalam STT"
            },
            {
                "id": "DEMO-2",
                "title": "DEMO 2 — Road Hazard Near School (English)",
                "raw_text": "There is a huge pothole near the primary school and children are crossing this road every morning.",
                "language": "en",
                "image_url": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=500",
                "latitude": 10.0312,
                "longitude": 76.3210,
                "expected": "Road Damage | High Safety Risk | High Priority"
            },
            {
                "id": "DEMO-3",
                "title": "DEMO 3 — Waste Accumulation (English)",
                "raw_text": "Garbage has not been collected for a week and it is overflowing near the public well.",
                "language": "en",
                "image_url": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=500",
                "latitude": 10.0220,
                "longitude": 76.3150,
                "expected": "Waste Management | Duration: 7 days | Critical"
            },
            {
                "id": "DEMO-4",
                "title": "DEMO 4 — Low Confidence Image Fallback",
                "raw_text": "Public structure issue near ward boundary.",
                "language": "en",
                "image_url": "https://images.unsplash.com/photo-1590059414006-30459b4b6842?w=500&q=ambiguous",
                "latitude": 10.0195,
                "longitude": 76.3050,
                "expected": "Low AI Confidence | Escalates to Human Review Queue"
            },
            {
                "id": "DEMO-5",
                "title": "DEMO 5 — Duplicate Issue Clustering",
                "raw_text": "Water pipeline broken on Ward 4 main road, no water arriving.",
                "language": "en",
                "image_url": None,
                "latitude": 10.0263,
                "longitude": 76.3127,
                "expected": "Clusters with existing Ward 4 Water Shortage issue"
            }
        ]
    }

@app.get("/api/evaluate")
def run_evaluation_endpoint():
    from evaluation.run import evaluate_gold_dataset
    results = evaluate_gold_dataset()
    return results
