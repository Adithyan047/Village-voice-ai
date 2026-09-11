import pytest
from app.db import init_db
from app.agents.graph import process_resident_report
from app.rag.store import rag_store
from app.tools.mcp_tools import calculate_priority

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_malayalam_water_complaint():
    res = process_resident_report(
        raw_text="മൂന്ന് ദിവസമായി ഞങ്ങളുടെ വീട്ടിൽ വെള്ളമില്ല.",
        language="ml"
    )
    assert res["language"] == "ml"
    assert res["category"] == "Water Supply"
    assert res["duration_days"] == 3
    assert res["priority_score"] >= 60
    assert res["confidence"] >= 0.85
    assert len(res["rag_sources"]) > 0

def test_english_road_complaint():
    res = process_resident_report(
        raw_text="There is a huge pothole near primary school."
    )
    assert res["category"] == "Roads"
    assert res["severity"] == "High"
    assert res["priority_score"] >= 50
    assert len(res["traces"]) >= 7

def test_low_confidence_escalation():
    res = process_resident_report(
        raw_text="Structure concern near border.",
        image_url="unclear_ambiguous.jpg"
    )
    assert res["needs_human_review"] == True
    assert res["routing_decision"] == "HUMAN_REVIEW"

def test_priority_calculation_tool():
    p = calculate_priority("High", 3, 15, 0.2, 3)
    assert p["total_priority"] >= 60
    assert "severity_score" in p

def test_rag_retrieval():
    rag_store.reload_documents()
    sources = rag_store.search("water supply complaint guidelines", category="Water Supply")
    assert len(sources) > 0
    assert "01_water_supply_guidelines.md" in [s["doc"] for s in sources]
