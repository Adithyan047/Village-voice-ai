# Emergency Escalation & Safety Guardrails

## 1. Safety Critic Protocols
Every issue processed by the multi-agent system undergoes Safety Critic review.

## 2. Mandatory Escalation Conditions
- Risk Score >= 0.60 OR Confidence Score < 0.60
- High safety hazard detected in visual analysis (e.g., exposed high voltage wires, landslide risk, contaminated drinking water near school).
- Discrepancy between visual evidence and text complaint.

## 3. Human Review Workflow
When flagged for Human Review:
1. Status set to `HUMAN_REVIEW`.
2. Summary sent to Authority Escalation Dashboard with full AI reasoning trace and ground citations.
3. Official can approve AI recommendation, override priority/category, or request field verification.
