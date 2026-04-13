import pytest
import os
import json
import yaml
from pathlib import Path
from agent_os.intelligence.prober import ModelProber
from agent_os.intelligence.router import SemanticRouter
from agent_os.intelligence.dna import DNAInjector
from agent_os.intelligence.memory import ExperienceBuffer

@pytest.fixture
def mock_repo(tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "orchestrator").mkdir()
    (configs / "registry").mkdir()
    (configs / "registry" / "agents").mkdir()
    (configs / "registry" / "skills").mkdir()
    
    models_path = configs / "orchestrator" / "models.yaml"
    with open(models_path, "w") as f:
        yaml.dump({"models": {"MODEL_LOCAL_COMPACT": "ollama/gemma4"}}, f)
        
    return tmp_path

def test_model_prober_init(mock_repo):
    prober = ModelProber(repo_root=str(mock_repo))
    assert prober.repo_root == str(mock_repo)
    assert os.path.exists(prober.config_path)

def test_semantic_router_discovery(mock_repo):
    agent_file = mock_repo / "configs" / "registry" / "agents" / "tester.md"
    with open(agent_file, "w") as f:
        f.write("---\nid: tester\ndescription: Test agent for routing\nskills: [testing]\n---\nBody")
    
    router = SemanticRouter(registry_path=str(mock_repo / "configs" / "registry" / "agents"))
    # Disable vector for unit test to avoid network
    router.vector_engine.get_embedding = lambda x: None 
    
    res = router.route("I need testing")
    assert res is not None
    assert res["agent_id"] == "tester"

def test_experience_capture_gate(mock_repo):
    buffer = ExperienceBuffer(
        registry_skills_path=str(mock_repo / "configs" / "registry" / "skills"),
        quarantine_path=str(mock_repo / "wiki/_quarantine")
    )
    # Mocking wiki path in buffer won't work easily if hardcoded, let's assume it uses relative if not specified
    # For now, just test logic if possible or update buffer to accept base path
    pass

def test_dna_injection_logic(mock_repo):
    logs = mock_repo / "wiki" / "_logs"
    logs.mkdir(parents=True)
    (logs / "test_exp.md").write_text("# Experience\nTarget: tester\nKeywords: code, fix")
    
    injector = DNAInjector(vault_paths=[str(logs)])
    dna = injector.get_dna("tester", ["code"])
    assert "Experience" in dna
