---
id: {{category}}-{{role-name}}
name: {{Display Name}}
version: 1.0.0
category: {{category}}
description: {{Short description of what the agent does and its primary value}}
personas:
  - operator
skills:
  - {{skill-1}}
  - {{skill-2}}
allowed_phases:
  - {{phase}}
preferred_models:
  - balanced_reasoner
tool_profile: {{profile}}
risk_level: low
output_contract:
  - {{output-1}}
---

# Mission
Define the absolute core purpose of this agent in 1-2 robust sentences. What is the single measure of its success?

# Must Do
- [ ] Explicit instruction 1 (e.g., "Always verify source code before modifying")
- [ ] Explicit instruction 2
- [ ] Explicit instruction 3

# Must Not Do
- [ ] Explicit boundary 1 (e.g., "Do not bypass testing phases")
- [ ] Explicit boundary 2
- [ ] Explicit boundary 3

# Execution Context
Provide context on how this agent typically interacts with the codebase, other agents, or human operators. What assumptions should it hold?

# Schema Output Format (if applicable)
If this agent generates structured data, define the expected schema or outline format here.
