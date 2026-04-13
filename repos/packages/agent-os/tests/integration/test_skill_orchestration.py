#!/usr/bin/env python3
"""Test Skill Orchestrator"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "repos/packages/agent-os/src"))

# Skip if orchestration module doesn't exist
try:
    from agent_os.orchestration.skill_orchestrator import SkillOrchestrator, TaskContext
except ImportError:
    pytest.skip("agent_os.orchestration module not available", allow_module_level=True)


def test_skill_trigger_detection():
    """Test skill trigger detection"""
    print("Testing skill trigger detection...")
    
    orchestrator = SkillOrchestrator("configs/skills/catalog/registry.yaml")
    
    # Test 1: Bug fix should trigger systematic-debugging
    task = TaskContext(
        task_type="T2",
        complexity="C2",
        description="Fix bug in payment validation"
    )
    triggered = orchestrator.detect_triggers(task)
    print(f"  Bug fix task triggers: {triggered}")
    assert "systematic-debugging" in triggered, "Should trigger systematic-debugging"
    
    # Test 2: Implementation should trigger verification
    task = TaskContext(
        task_type="T3",
        complexity="C3",
        description="Implement REST API endpoint with validation"
    )
    triggered = orchestrator.detect_triggers(task)
    print(f"  Implementation task triggers: {triggered}")
    assert "verification-before-completion" in triggered, "Should trigger verification"
    
    # Test 3: Architecture should trigger planning
    task = TaskContext(
        task_type="T4",
        complexity="C4",
        description="Refactor payment module architecture"
    )
    triggered = orchestrator.detect_triggers(task)
    print(f"  Architecture task triggers: {triggered}")
    assert "writing-plans" in triggered, "Should trigger writing-plans"
    
    # Test 4: C5 should trigger subagent
    task = TaskContext(
        task_type="T4",
        complexity="C5",
        description="Security audit and compliance"
    )
    triggered = orchestrator.detect_triggers(task)
    print(f"  C5 task triggers: {triggered}")
    assert "subagent-driven-development" in triggered, "Should trigger subagent"
    
    print("✓ All skill trigger tests passed\n")
    return True


def test_skill_activation():
    """Test skill activation"""
    print("Testing skill activation...")
    
    orchestrator = SkillOrchestrator("configs/skills/catalog/registry.yaml")
    
    skills = ["systematic-debugging", "test-driven-development"]
    contexts = orchestrator.activate_skills(skills)
    
    print(f"  Activated {len(contexts)} skills")
    assert len(contexts) == 2, "Should activate 2 skills"
    assert "systematic-debugging" in contexts
    assert "test-driven-development" in contexts
    
    for skill_id, data in contexts.items():
        print(f"    - {skill_id}: {data['active']}")
        assert data["active"] == True
    
    print("✓ Skill activation test passed\n")
    return True


def main():
    print("=" * 60)
    print("SKILL ORCHESTRATOR TESTS")
    print("=" * 60)
    print()
    
    try:
        test_skill_trigger_detection()
        test_skill_activation()
        
        print("=" * 60)
        print("Phase 3 Complete: Skill Orchestration working")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
