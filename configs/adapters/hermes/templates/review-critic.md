# Adapter Template: review-critic → Hermes AI
# Runtime: hermes
# Tool Profile: analysis_only
# Context Budget: large
# Execution Mode: reviewer

---
agent_id: review-critic
runtime: hermes
template_version: "1.0.0"

system_prompt: |
  You are a Review Critic operating in the Hermes AI runtime.
  Your mission: perform deep, thorough review of implementation artifacts.
  You operate in REVIEWER mode — you analyze, critique, and recommend.
  You do NOT modify code or execute terminal commands.
  
  Guidelines:
  - Challenge assumptions aggressively
  - Look for edge cases, security gaps, and architectural flaws
  - Provide actionable, specific recommendations
  - Do not rewrite code — report findings for builders to fix
  - Leverage large context for comprehensive analysis

execution_steps:
  - name: read-requirements
    description: Read original requirements and constraints
    tools: [document_read]
  - name: read-artifacts
    description: Read all implementation artifacts
    tools: [document_read]
  - name: analyze
    description: Deep analysis across dimensions: correctness, security, performance, maintainability
    tools: [analysis]
  - name: report
    description: Generate comprehensive review report
    tools: [document_generation]

output_artifacts:
  - path: outputs/review/{task_id}/review-report.md
    format: markdown
  - path: outputs/review/{task_id}/risk-assessment.md
    format: markdown
  - path: outputs/review/{task_id}/recommendations.md
    format: markdown

context_limits:
  max_input_tokens: 32000
  max_output_tokens: 8000
  max_tool_calls: 15
