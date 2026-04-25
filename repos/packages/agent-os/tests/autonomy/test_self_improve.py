import pytest
from pathlib import Path
from agent_os.self_improve import SelfReferentialAgent

@pytest.fixture
def agent_root(tmp_path):
    # Setup a mock package structure
    src = tmp_path / "src"
    src.mkdir()
    (src / "planner.py").write_text("def plan(goal): return f'Plan for {goal}'", encoding="utf-8")
    return src

def test_inspect_self(agent_root):
    agent = SelfReferentialAgent(agent_root)
    code = agent.inspect_self("planner")
    assert "def plan(goal)" in code

def test_evaluate_utility(agent_root):
    agent = SelfReferentialAgent(agent_root)
    
    def mock_policy(goal):
        if goal == "fail":
            raise ValueError("Error")
        return "Success"
    
    # Test success
    eval_ok = agent.execute_and_evaluate("test", mock_policy)
    assert eval_ok["utility"] > 0
    assert eval_ok["error_trace"] is None
    
    # Test failure
    eval_fail = agent.execute_and_evaluate("fail", mock_policy)
    assert eval_fail["utility"] <= 0
    assert eval_fail["error_trace"] == "Error"

def test_apply_patch(agent_root):
    agent = SelfReferentialAgent(agent_root)
    patch_path = agent.apply_patch("planner", "def improved_plan(goal): pass", "v2")
    
    assert patch_path.exists()
    assert "improved_plan" in patch_path.read_text()
