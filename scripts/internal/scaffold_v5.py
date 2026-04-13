import os
from pathlib import Path

def create_structure(base_dir: str):
    root = Path(base_dir)
    
    dirs = [
        "configs/orchestrator",
        "configs/registry/agents/core",
        "configs/registry/agents/research",
        "configs/registry/agents/architecture",
        "configs/registry/agents/execution",
        "configs/registry/agents/review",
        "configs/registry/agents/design",
        "configs/registry/agents/growth",
        "configs/registry/agents/ops",
        "configs/registry/agents/domain",
        "configs/registry/skills/core",
        "configs/registry/skills/ingestion",
        "configs/registry/skills/analysis",
        "configs/registry/skills/generation",
        "configs/registry/skills/validation",
        "configs/registry/skills/export",
        "configs/registry/skills/memory",
        "configs/registry/workflows/research",
        "configs/registry/workflows/engineering",
        "configs/registry/workflows/content",
        "configs/registry/workflows/strategy",
        "configs/registry/workflows/estimation",
        "configs/registry/personas",
        "configs/registry/policies/global",
        "configs/registry/policies/safety",
        "configs/registry/policies/style",
        "configs/registry/policies/quality",
        "configs/registry/policies/runtime",
        "configs/registry/schemas",
        "configs/registry/taxonomies",
        "configs/registry/indexes",
        "configs/adapters/antigravity/templates",
        "configs/adapters/antigravity/wrappers",
        "configs/adapters/antigravity/tests",
        "configs/adapters/hermes/templates",
        "configs/adapters/hermes/wrappers",
        "configs/adapters/hermes/tests",
        "configs/adapters/claude-code",
        "configs/adapters/codex",
        "configs/adapters/opencode",
        "docs/architecture",
        "docs/standards",
        "docs/playbooks",
        "repos/runtime/antigravity-pack",
        "repos/runtime/hermes-pack",
        "repos/runtime/shared",
        "repos/imported/upstream-agents",
        "repos/imported/upstream-skills",
        "repos/imported/upstream-templates",
        "repos/tools/registry-lint",
        "repos/tools/adapter-compiler",
        "repos/tools/workflow-runner",
        "repos/tools/manifest-builder",
        "memory/raw",
        "memory/distilled",
        "memory/decisions",
        "memory/logs",
        "outputs/generated",
        "outputs/exports",
        "outputs/reports",
        "sandbox/experiments",
        "sandbox/adapter-tests",
        "sandbox/migration",
        "sandbox/fixture-projects",
    ]

    files = {
        "configs/orchestrator/models.yaml": "",
        "configs/orchestrator/runtimes.yaml": "",
        "configs/orchestrator/routing.yaml": "",
        "configs/orchestrator/permissions.yaml": "",
        "configs/orchestrator/phases.yaml": "",
        "configs/orchestrator/budgets.yaml": "",
        "configs/orchestrator/defaults.yaml": "",
        "configs/registry/schemas/agent.schema.yaml": "",
        "configs/registry/schemas/skill.schema.yaml": "",
        "configs/registry/schemas/workflow.schema.yaml": "",
        "configs/registry/schemas/persona.schema.yaml": "",
        "configs/registry/schemas/adapter.schema.yaml": "",
        "configs/registry/taxonomies/domains.yaml": "",
        "configs/registry/taxonomies/tools.yaml": "",
        "configs/registry/taxonomies/phases.yaml": "",
        "configs/registry/taxonomies/priorities.yaml": "",
        "configs/registry/taxonomies/risk-levels.yaml": "",
        "configs/registry/indexes/agents.index.yaml": "agents: []\n",
        "configs/registry/indexes/skills.index.yaml": "skills: []\n",
        "configs/registry/indexes/workflows.index.yaml": "workflows: []\n",
    }

    # Create directories
    for d in dirs:
        dir_path = root / d
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

    # Create files
    for f, content in files.items():
        file_path = root / f
        if not file_path.exists():
            file_path.write_text(content)
            print(f"Created file: {file_path}")

if __name__ == "__main__":
    create_structure(".")
    print("✅ Schema scaffolding complete!")
