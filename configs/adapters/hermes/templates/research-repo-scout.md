# Adapter Template: research-repo-scout → Hermes AI
# Runtime: hermes
# Tool Profile: web_research
# Context Budget: large
# Execution Mode: planner

---
agent_id: research-repo-scout
runtime: hermes
template_version: "1.0.0"

system_prompt: |
  You are a Repository Scout operating in the Hermes AI runtime.
  Your mission: analyze, plan, and produce a structured repository shortlist.
  You operate in PLANNER mode — you research, analyze, and produce recommendations.
  You do NOT perform code surgery or terminal operations.
  
  Guidelines:
  - Score by adoption fit, not just popularity
  - Flag lock-in risks
  - Separate core candidates from donor candidates
  - Produce detailed analysis with reasoning

execution_steps:
  - name: discover
    description: Research and discover relevant repositories
    tools: [web_research]
  - name: analyze
    description: Perform deep analysis of architecture, quality, adoption fit
    tools: [web_research, analysis]
  - name: score
    description: Score candidates against integration criteria with detailed reasoning
    tools: [analysis]
  - name: report
    description: Generate comprehensive research report
    tools: [document_generation]

output_artifacts:
  - path: outputs/research/{task_id}/shortlist.md
    format: markdown
  - path: outputs/research/{task_id}/analysis-report.md
    format: markdown
  - path: outputs/research/{task_id}/scoring-matrix.json
    format: json

context_limits:
  max_input_tokens: 32000
  max_output_tokens: 8000
  max_tool_calls: 20
