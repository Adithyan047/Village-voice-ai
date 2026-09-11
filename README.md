# VILLAGE VOICE — AI-Powered Rural Community Issue Intelligence Platform

Track: Track 04 — Sustainability, Smart Infrastructure & Future Communities  
Repository: Village Voice Agentic AI Hackathon Submission  
Frameworks: Python, FastAPI, LangGraph, RAG Vector Guidelines, SQLite, Leaflet GIS, Tailwind CSS  

---

## 1. PROBLEM STATEMENT

Rural communities across India frequently experience severe public infrastructure disruptions, including prolonged drinking water outages, hazardous road potholes near schools, uncollected waste accumulation, open sewage flooding, and snapping electrical wires.

Residents face substantial barriers when reporting these issues due to:
1. Language and Dialect Constraints: Inability to write formal complaints in standard English or Hindi (e.g., native Malayalam dialect speakers).
2. Digital Literacy Limits: Complex governmental portals requiring multi-step formal typing.
3. Siloed Municipal Routing: Single complaints get buried in bureaucratic backlogs rather than being aggregated into community-level priorities.

Village Voice addresses this challenge by converting unstructured Malayalam and English voice audio, raw text, photos, and GPS pins into structured, clustered, prioritized, and safety-audited civic issues.

---

## 2. ARCHITECTURE SKETCH

```
                 RESIDENT INPUT
     (Malayalam/English Voice, Text, Image, GPS)
                        │
                        ▼
               ┌────────────────┐
               │  Intake Agent  │ (Malayalam STT, Normalization, Entity Extraction)
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │   Classifier   │ (Taxonomy Mapping & Severity Audit)
               └───────┬────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌──────────────┐┌──────────────┐┌──────────────┐
│ RAG Retriever││ Image Agent  ││   Geo Tool   │
└──────┬───────┘└──────┬───────┘└──────┬───────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
               ┌────────────────┐
               │Clustering Agent│ (Group N Reports -> 1 Community Issue)
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │ Priority Agent │ (Score: 0.30*Sev + 0.20*Dur + 0.20*Pop + 0.20*Risk + 0.10*Reps)
               └───────┬────────┘
                       │
                       ▼
               ┌────────────────┐
               │ Safety Critic  │ (Confidence Audit & Risk Assessment)
               └───────┬────────┘
                       │
               ┌───────┴───────┐
               ▼               ▼
       [ Auto Process ]   [ Human Escalation Queue ]
               │               │
               └───────┬────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ GIS Map + Authority  │
            │ Dashboard + AI Trace │
            └──────────────────────┘
```

---

## 3. HOW THE SAFETY & CONFIDENCE CHECK BEHAVES

The Safety & Confidence Critic Agent acts as a mandatory guardrail that audits every report before municipal dispatch or automated routing takes place:

1. Dual Metric Calculation:
   - AI Confidence Score (0.0 to 1.0): Evaluates linguistic entity clarity and visual classification certainty.
   - Public Safety Risk Score (0.0 to 1.0): Measures immediate physical danger (e.g., exposed high-voltage wires, sewage near drinking wells, landslides).

2. Decision Rules:
   - Auto-Process (Confidence >= 0.80 AND Risk < 0.60): Issue is automatically structured, prioritized, assigned to the responsible department (e.g., Kerala Water Authority), and plotted on the GIS map.
   - Human Escalation Queue (Confidence < 0.60 OR Risk >= 0.60): The system refuses to auto-route. It flags the report as HUMAN_REVIEW and routes it to the Authority Escalation Queue along with the AI reasoning, original Malayalam transcription, visual evidence, and RAG grounding citations.
   - Categorical Fallback: Unclassified or general issues are mandatorily directed to human municipal inspection.

---

## 4. AUTHORITY VIEW SECURITY & PASSWORD PROTECTION

The Authority Portal is protected by a master password requirement:
1. First Time Setup: Upon first clicking "Authority Portal", the system prompts the administrator to set up a master password.
2. Master Password Verification: Subsequent visits require entering the password to unlock the authority dashboard, issue details, and workflow controls.
3. Portal Locking: Administrators can lock the portal session at any time.

---

## 5. MULTI-AGENT ORCHESTRATION & MCP TOOLS

### LangGraph Agent Nodes
- Intake Agent: Normalizes Malayalam audio/text, extracts duration and ward metadata.
- Classification Agent: Enforces strict taxonomy (Water Supply, Roads, Waste Management, Sanitation, Electricity, Streetlight, Drainage, Other).
- Knowledge Retriever Agent: Performs RAG vector search across rural guidelines (01_water_supply_guidelines.md to 08_emergency_escalation_guidelines.md) for grounded SOP citations.
- Image Analysis Agent: Multimodal visual risk inspection.
- Clustering Agent: Groups duplicate ward reports into a single Community Issue (12 resident reports -> 1 Community Issue).
- Priority Agent: Computes transparent multi-factor score:
  Priority = 0.30 * Severity + 0.20 * Duration + 0.20 * Population + 0.20 * Safety Risk + 0.10 * Reports
- Safety Critic Agent: Enforces guardrail audit.
- Router Agent: Persists issue state and outputs observability traces.

### MCP Callable Tools
get_location_context, search_civic_guidelines, find_similar_issues, calculate_priority, create_issue, update_issue_status, assign_issue, notify_authority, get_issue_history, record_feedback.

---

## 6. GOLD BENCHMARK EVALUATION RESULTS

Run using:
```bash
python -m evaluation.run
```
- Total Test Cases: 20 Gold Trajectories
- Classification Accuracy: 85.0%
- Severity Accuracy: 90.0%
- Priority Scoring Accuracy: 100.0%
- Safety Escalation Accuracy: 100.0%

---

## 7. QUICKSTART INSTRUCTIONS

1. Start backend server:
   ```bash
   cd backend
   py -m uvicorn app.main:app --port 8000 --host 0.0.0.0
   ```
2. Open http://localhost:8000 in any browser.
3. Test preloaded hackathon presets from the top dropdown:
   - DEMO 1 (Malayalam Water Shortage): മൂന്ന് ദിവസമായി ഞങ്ങളുടെ വീട്ടിൽ വെള്ളമില്ല.
   - DEMO 2 (Road Hazard near School): High safety risk pothole.
   - DEMO 3 (Overflowing Waste): Rotting waste > 7 days.
   - DEMO 4 (Low Confidence Image): Triggers Human Escalation Queue.
   - DEMO 5 (Duplicate Clustering): Merges Ward 4 reports into 1 issue.
