from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ReportCreate(BaseModel):
    raw_text: Optional[str] = None
    language: Optional[str] = "en"
    audio_base64: Optional[str] = None
    image_url: Optional[str] = None
    latitude: float = 10.0261
    longitude: float = 76.3125
    ward: Optional[str] = "Ward 4"

class ReportResponse(BaseModel):
    id: str
    issue_id: Optional[str] = None
    original_text: str
    normalized_text: str
    language: str
    category: str
    severity: str
    duration_days: int
    confidence: float
    latitude: float
    longitude: float
    ward: str
    image_url: Optional[str] = None
    created_at: str

class PriorityBreakdown(BaseModel):
    severity_score: float
    duration_score: float
    population_score: float
    safety_risk_score: float
    reports_score: float
    total_priority: float
    reasoning: str

class IssueResponse(BaseModel):
    id: str
    title: str
    category: str
    subcategory: str
    priority_score: int
    severity: str
    duration_days: int
    affected_reports_count: int
    status: str  # REPORTED, ASSIGNED, IN_PROGRESS, RESOLVED, HUMAN_REVIEW
    assigned_department: str
    latitude: float
    longitude: float
    ward: str
    confidence: float
    risk_score: float
    needs_human_review: bool
    escalation_reason: Optional[str] = None
    priority_breakdown: PriorityBreakdown
    rag_sources: List[Dict[str, str]]
    image_analysis: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class AgentTraceStep(BaseModel):
    timestamp: str
    agent_name: str
    action: str
    input_summary: str
    output_summary: str
    confidence: float
    tool_calls: List[str]
    retrieved_sources: List[str]
    decision: str

class FeedbackCreate(BaseModel):
    issue_id: str
    resolved: bool
    useful_info: bool
    comments: Optional[str] = None
