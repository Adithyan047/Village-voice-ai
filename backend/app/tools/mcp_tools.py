import json
from typing import Dict, Any, List, Optional
from app.rag.store import rag_store
from app.db import get_db_connection

def get_location_context(latitude: float, longitude: float) -> Dict[str, Any]:
    """MCP Tool: Retrieves ward, nearest landmark, and regional risk factors from GIS coordinates."""
    # Simple spatial lookup / mock GIS context
    if 10.0200 <= latitude <= 10.0350 and 76.3000 <= longitude <= 76.3200:
        return {
            "ward": "Ward 4",
            "locality": "Kizhakkambalam East",
            "district": "Ernakulam",
            "sensitive_zones": ["Panchayat Primary School", "Community Health Center"],
            "historical_flooding_risk": "Medium"
        }
    return {
        "ward": "Ward 2",
        "locality": "Panchayat Market Zone",
        "district": "Ernakulam",
        "sensitive_zones": ["Public Bus Stand"],
        "historical_flooding_risk": "Low"
    }

def search_civic_guidelines(query: str, category: str = "") -> List[Dict[str, str]]:
    """MCP Tool: Searches vector knowledge base for grounded civic resolution guidelines."""
    return rag_store.search(query, category=category, top_k=2)

def find_similar_issues(category: str, latitude: float, longitude: float, distance_km: float = 1.0) -> List[Dict[str, Any]]:
    """MCP Tool: Queries database for existing open issues matching spatial and category criteria for clustering."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM issues 
        WHERE category = ? AND status != 'RESOLVED'
    """, (category,))
    rows = cursor.fetchall()
    conn.close()

    similar = []
    for r in rows:
        # Distance approximation
        lat_diff = abs(r["latitude"] - latitude)
        lon_diff = abs(r["longitude"] - longitude)
        if lat_diff < 0.02 and lon_diff < 0.02:
            similar.append({
                "issue_id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "affected_reports": r["affected_reports_count"],
                "status": r["status"]
            })
    return similar

def calculate_priority(severity: str, duration_days: int, affected_pop_est: int, safety_risk: float, num_reports: int) -> Dict[str, Any]:
    """MCP Tool: Computes explicit multi-factor priority score (0-100) using weight formula."""
    sev_map = {"Low": 30, "Medium": 60, "High": 85, "Critical": 100}
    sev_score = sev_map.get(severity, 50)
    
    dur_score = min(duration_days * 20, 100)
    pop_score = min(affected_pop_est * 8, 100)
    risk_score = int(safety_risk * 100)
    reports_score = min(num_reports * 25, 100)

    # Priority Formula: 0.30 * Sev + 0.20 * Dur + 0.20 * Pop + 0.20 * SafetyRisk + 0.10 * Reports
    priority = (
        0.30 * sev_score +
        0.20 * dur_score +
        0.20 * pop_score +
        0.20 * risk_score +
        0.10 * reports_score
    )
    
    total = int(min(max(priority, 10), 100))
    
    reason = f"Severity: {sev_score}, Duration: {dur_score}, Affected Pop: {pop_score}, Safety Risk: {risk_score}, Reports: {reports_score}."
    
    return {
        "severity_score": sev_score,
        "duration_score": dur_score,
        "population_score": pop_score,
        "safety_risk_score": risk_score,
        "reports_score": reports_score,
        "total_priority": total,
        "reasoning": reason
    }

def create_issue(issue_data: Dict[str, Any], conn=None) -> str:
    """MCP Tool: Creates a new community issue record in the database."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO issues (id, title, category, subcategory, priority_score, severity, duration_days, affected_reports_count, status, assigned_department, latitude, longitude, ward, confidence, risk_score, needs_human_review, escalation_reason, priority_breakdown, rag_sources, image_analysis, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        issue_data["id"],
        issue_data["title"],
        issue_data["category"],
        issue_data["subcategory"],
        issue_data["priority_score"],
        issue_data["severity"],
        issue_data["duration_days"],
        issue_data["affected_reports_count"],
        issue_data["status"],
        issue_data["assigned_department"],
        issue_data["latitude"],
        issue_data["longitude"],
        issue_data["ward"],
        issue_data["confidence"],
        issue_data["risk_score"],
        1 if issue_data["needs_human_review"] else 0,
        issue_data.get("escalation_reason"),
        json.dumps(issue_data["priority_breakdown"]),
        json.dumps(issue_data["rag_sources"]),
        json.dumps(issue_data.get("image_analysis")),
        issue_data["created_at"],
        issue_data["updated_at"]
    ))
    if should_close:
        conn.commit()
        conn.close()
    return issue_data["id"]

def update_issue_status(issue_id: str, new_status: str) -> bool:
    """MCP Tool: Updates issue status (Reported -> Assigned -> In Progress -> Resolved)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET status = ?, updated_at = datetime('now') WHERE id = ?", (new_status, issue_id))
    conn.commit()
    conn.close()
    return True

def assign_issue(issue_id: str, department: str) -> bool:
    """MCP Tool: Assigns issue to specific local authority department."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE issues SET assigned_department = ?, status = 'ASSIGNED', updated_at = datetime('now') WHERE id = ?", (department, issue_id))
    conn.commit()
    conn.close()
    return True

def notify_authority(issue_id: str, priority: int, department: str) -> Dict[str, Any]:
    """MCP Tool: Triggers automated dispatch notification to authority contacts."""
    return {
        "status": "NOTIFIED",
        "issue_id": issue_id,
        "recipient": f"{department} Mobile Liaison Unit",
        "dispatch_timestamp": "NOW"
    }

def get_issue_history(issue_id: str) -> List[Dict[str, Any]]:
    """MCP Tool: Retrieves audit history of all reports and agent steps for an issue."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traces WHERE issue_id = ? ORDER BY id ASC", (issue_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def record_feedback(issue_id: str, resolved: bool, useful_info: bool, comments: str = "") -> bool:
    """MCP Tool: Records resident satisfaction feedback."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO feedback (issue_id, resolved, useful_info, comments, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                   (issue_id, 1 if resolved else 0, 1 if useful_info else 0, comments))
    conn.commit()
    conn.close()
    return True
