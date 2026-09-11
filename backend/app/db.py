import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "village_voice.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Reports table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        issue_id TEXT,
        original_text TEXT NOT NULL,
        normalized_text TEXT NOT NULL,
        language TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        confidence REAL NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        ward TEXT NOT NULL,
        image_url TEXT,
        created_at TEXT NOT NULL
    )
    ''')

    # Issues table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS issues (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        priority_score INTEGER NOT NULL,
        severity TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        affected_reports_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        assigned_department TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        ward TEXT NOT NULL,
        confidence REAL NOT NULL,
        risk_score REAL NOT NULL,
        needs_human_review INTEGER NOT NULL,
        escalation_reason TEXT,
        priority_breakdown TEXT NOT NULL,
        rag_sources TEXT NOT NULL,
        image_analysis TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')

    # Traces table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT NOT NULL,
        issue_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        action TEXT NOT NULL,
        input_summary TEXT NOT NULL,
        output_summary TEXT NOT NULL,
        confidence REAL NOT NULL,
        tool_calls TEXT NOT NULL,
        retrieved_sources TEXT NOT NULL,
        decision TEXT NOT NULL
    )
    ''')

    # Feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id TEXT NOT NULL,
        resolved INTEGER NOT NULL,
        useful_info INTEGER NOT NULL,
        comments TEXT,
        created_at TEXT NOT NULL
    )
    ''')

    conn.commit()

    # Pre-seed demo data if empty
    cursor.execute("SELECT COUNT(*) FROM issues")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_demo_data(cursor)
        conn.commit()

    conn.close()

def seed_demo_data(cursor):
    now = datetime.now().isoformat()
    
    # Pre-seeded Issue 1: Ward 4 Water Shortage (Clustered Community Issue)
    issue1_breakdown = json.dumps({
        "severity_score": 90,
        "duration_score": 80,
        "population_score": 95,
        "safety_risk_score": 90,
        "reports_score": 95,
        "total_priority": 91,
        "reasoning": "Multiple reports indicate prolonged water shortage exceeding 72 hours affecting 12+ households in Ward 4."
    })
    issue1_rag = json.dumps([
        {
            "doc": "01_water_supply_guidelines.md",
            "title": "Rural Water Supply Guidelines",
            "citation": "Section 2: Critical Severity (Duration > 48 hours mandate emergency tanker supply)"
        },
        {
            "doc": "07_department_routing_guide.md",
            "title": "Department Routing Guide",
            "citation": "Water Supply -> Kerala Water Authority (KWA) / PHED Wing"
        }
    ])
    
    cursor.execute('''
    INSERT INTO issues (id, title, category, subcategory, priority_score, severity, duration_days, affected_reports_count, status, assigned_department, latitude, longitude, ward, confidence, risk_score, needs_human_review, escalation_reason, priority_breakdown, rag_sources, image_analysis, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "ISSUE-W4-01",
        "Severe Drinking Water Shortage - Ward 4",
        "Water Supply",
        "Public Pipeline Disruption",
        91,
        "High",
        3,
        12,
        "Reported",
        "Kerala Water Authority (KWA)",
        10.0261,
        76.3125,
        "Ward 4",
        0.94,
        0.20,
        0,
        None,
        issue1_breakdown,
        issue1_rag,
        json.dumps({"detected_issue": "Dry tap / broken pipe joint", "confidence": 0.92, "safety_risk": 0.15}),
        now,
        now
    ))

    # Seed Reports for Issue 1
    cursor.execute('''
    INSERT INTO reports (id, issue_id, original_text, normalized_text, language, category, severity, duration_days, confidence, latitude, longitude, ward, image_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "REP-001",
        "ISSUE-W4-01",
        "മൂന്ന് ദിവസമായി ഞങ്ങളുടെ വീട്ടിൽ വെള്ളമില്ല.",
        "No water supply in our house for three days.",
        "ml",
        "Water Supply",
        "High",
        3,
        0.94,
        10.0261,
        76.3125,
        "Ward 4",
        "https://images.unsplash.com/photo-1541888946425-d0fbb186a5b3?w=500",
        now
    ))

    cursor.execute('''
    INSERT INTO reports (id, issue_id, original_text, normalized_text, language, category, severity, duration_days, confidence, latitude, longitude, ward, image_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "REP-002",
        "ISSUE-W4-01",
        "Water supply disrupted in Ward 4 main street since Tuesday.",
        "Water supply disrupted in Ward 4 main street since Tuesday.",
        "en",
        "Water Supply",
        "High",
        3,
        0.92,
        10.0265,
        76.3128,
        "Ward 4",
        None,
        now
    ))

    # Pre-seeded Issue 2: Road Hazard near School
    issue2_breakdown = json.dumps({
        "severity_score": 85,
        "duration_score": 70,
        "population_score": 85,
        "safety_risk_score": 95,
        "reports_score": 60,
        "total_priority": 83,
        "reasoning": "Large deep pothole on primary school access route presenting immediate safety hazard for children."
    })
    issue2_rag = json.dumps([
        {
            "doc": "02_road_damage_guidelines.md",
            "title": "Road Infrastructure Guidelines",
            "citation": "Section 2: High Safety Risk near school zones mandates immediate warning sign placement and emergency patching."
        }
    ])

    cursor.execute('''
    INSERT INTO issues (id, title, category, subcategory, priority_score, severity, duration_days, affected_reports_count, status, assigned_department, latitude, longitude, ward, confidence, risk_score, needs_human_review, escalation_reason, priority_breakdown, rag_sources, image_analysis, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "ISSUE-RD-02",
        "Deep Pothole Hazard near St. Mary's School",
        "Roads",
        "Hazardous Pothole",
        83,
        "High",
        5,
        4,
        "In Progress",
        "Public Works Department (PWD)",
        10.0312,
        76.3210,
        "Ward 2",
        0.89,
        0.45,
        0,
        None,
        issue2_breakdown,
        issue2_rag,
        json.dumps({"detected_issue": "Large asphalt road depression", "confidence": 0.88, "safety_risk": 0.80}),
        now,
        now
    ))

    # Pre-seeded Issue 3: Low Confidence / Human Review Escalated Issue
    issue3_breakdown = json.dumps({
        "severity_score": 60,
        "duration_score": 40,
        "population_score": 50,
        "safety_risk_score": 70,
        "reports_score": 30,
        "total_priority": 56,
        "reasoning": "Ambiguous image and low confidence report requiring official verification."
    })
    issue3_rag = json.dumps([
        {
            "doc": "08_emergency_escalation_guidelines.md",
            "title": "Emergency Escalation Guidelines",
            "citation": "Section 2: Confidence Score < 0.60 requires mandatory routing to Human Escalation Queue."
        }
    ])

    cursor.execute('''
    INSERT INTO issues (id, title, category, subcategory, priority_score, severity, duration_days, affected_reports_count, status, assigned_department, latitude, longitude, ward, confidence, risk_score, needs_human_review, escalation_reason, priority_breakdown, rag_sources, image_analysis, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "ISSUE-ESC-03",
        "Unclear Infrastructure Damage - Requires Inspection",
        "Other",
        "Unverified Public Structure",
        56,
        "Medium",
        1,
        1,
        "HUMAN_REVIEW",
        "Gram Panchayat Engineering Wing",
        10.0195,
        76.3050,
        "Ward 6",
        0.52,
        0.65,
        1,
        "Low AI confidence (0.52) and ambiguous image evidence. Flagged by Safety Critic.",
        issue3_breakdown,
        issue3_rag,
        json.dumps({"detected_issue": "Ambiguous structural shadow", "confidence": 0.45, "safety_risk": 0.65}),
        now,
        now
    ))

if __name__ == "__main__":
    init_db()
    print("Database initialized and pre-seeded successfully.")
