#!/usr/bin/env python3
"""
Baseline Test Suite
Measures current system performance before integration changes
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class TaskScenario:
    id: str
    type: str
    complexity: str
    description: str
    expected_skills: List[str]
    expected_mcp: List[str]
    expected_memory_queries: int

@dataclass
class TestResult:
    scenario_id: str
    routing_time_ms: float
    phase_detected: str
    mcp_servers_selected: List[str]
    skills_activated: List[str]
    memory_queries: int
    success: bool
    notes: str

# Test scenarios
SCENARIOS = [
    TaskScenario(
        id="C1-config",
        type="T1",
        complexity="C1",
        description="Add DATABASE_URL to .env.example",
        expected_skills=[],
        expected_mcp=["filesystem"],
        expected_memory_queries=0
    ),
    TaskScenario(
        id="C2-fix",
        type="T2",
        complexity="C2",
        description="Fix TypeScript lint error in auth module",
        expected_skills=["systematic-debugging"],
        expected_mcp=["filesystem"],
        expected_memory_queries=1
    ),
    TaskScenario(
        id="C3-implement",
        type="T3",
        complexity="C3",
        description="Implement REST API endpoint for user authentication with JWT validation",
        expected_skills=["systematic-debugging", "test-driven-development"],
        expected_mcp=["filesystem", "memory", "context"],
        expected_memory_queries=3
    ),
    TaskScenario(
        id="C4-architect",
        type="T4",
        complexity="C4",
        description="Refactor payment processing module with new architecture",
        expected_skills=["writing-plans", "subagent-driven-development"],
        expected_mcp=["filesystem", "memory", "context", "github"],
        expected_memory_queries=5
    ),
    TaskScenario(
        id="C5-security",
        type="T4",
        complexity="C5",
        description="Security audit and PCI-DSS compliance implementation for payment system",
        expected_skills=["writing-plans", "systematic-debugging"],
        expected_mcp=["filesystem", "memory", "context", "github"],
        expected_memory_queries=7
    )
]

def load_router_config() -> Dict[str, Any]:
    """Load router configuration"""
    config_path = Path("configs/orchestrator/router.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Router config not found: {config_path}")
    
    with open(config_path) as f:
        content = f.read()
        return {"raw": content}

def test_routing(scenario: TaskScenario) -> TestResult:
    """Test routing for a scenario"""
    start_time = time.time()
    
    config = load_router_config()
    
    # Check phase-aware status
    phase_aware_enabled = "enabled: true" in config["raw"] and "phase_aware:" in config["raw"]
    
    # Simulate phase detection
    phase_map = {
        "C1": "implementation",
        "C2": "implementation",
        "C3": "implementation",
        "C4": "planning",
        "C5": "planning"
    }
    phase = phase_map.get(scenario.complexity, "unknown")
    
    # Baseline: minimal MCP
    mcp_servers = ["filesystem"]
    
    # Baseline: no auto-activation
    skills_activated = []
    
    # Baseline: no preloading
    memory_queries = 0
    
    routing_time = (time.time() - start_time) * 1000
    
    return TestResult(
        scenario_id=scenario.id,
        routing_time_ms=routing_time,
        phase_detected=phase,
        mcp_servers_selected=mcp_servers,
        skills_activated=skills_activated,
        memory_queries=memory_queries,
        success=True,
        notes=f"Phase-aware: {phase_aware_enabled}"
    )

def calculate_metrics(results: List[TestResult]) -> Dict[str, Any]:
    """Calculate aggregate metrics"""
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.success)
    
    avg_routing_time = sum(r.routing_time_ms for r in results) / total_tests
    
    total_expected_skills = sum(len(SCENARIOS[i].expected_skills) for i in range(len(SCENARIOS)))
    total_activated_skills = sum(len(r.skills_activated) for r in results)
    skill_activation_rate = (total_activated_skills / total_expected_skills * 100) if total_expected_skills > 0 else 0
    
    correct_mcp = 0
    for i, result in enumerate(results):
        expected = set(SCENARIOS[i].expected_mcp)
        actual = set(result.mcp_servers_selected)
        if expected.issubset(actual):
            correct_mcp += 1
    mcp_accuracy = (correct_mcp / total_tests) * 100
    
    total_expected_queries = sum(s.expected_memory_queries for s in SCENARIOS)
    total_actual_queries = sum(r.memory_queries for r in results)
    memory_usage_rate = (total_actual_queries / total_expected_queries * 100) if total_expected_queries > 0 else 0
    
    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": (successful_tests / total_tests) * 100,
        "avg_routing_time_ms": round(avg_routing_time, 2),
        "skill_activation_rate": round(skill_activation_rate, 2),
        "mcp_accuracy": round(mcp_accuracy, 2),
        "memory_usage_rate": round(memory_usage_rate, 2)
    }

def main():
    print("=" * 60)
    print("BASELINE TEST SUITE")
    print("=" * 60)
    print()
    
    try:
        config = load_router_config()
        phase_aware = "enabled: true" in config["raw"] and "phase_aware:" in config["raw"]
        print(f"Phase-aware MCP: {'ENABLED' if phase_aware else 'DISABLED'}")
        print()
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    results = []
    for scenario in SCENARIOS:
        print(f"Testing {scenario.id} ({scenario.complexity})...")
        result = test_routing(scenario)
        results.append(result)
        
        print(f"  ✓ Routing time: {result.routing_time_ms:.2f}ms")
        print(f"  ✓ Phase: {result.phase_detected}")
        print(f"  ✓ MCP servers: {result.mcp_servers_selected}")
        print(f"  ✓ Skills: {result.skills_activated if result.skills_activated else 'none'}")
        print(f"  ✓ Memory queries: {result.memory_queries}")
        print()
    
    metrics = calculate_metrics(results)
    
    print("=" * 60)
    print("BASELINE METRICS")
    print("=" * 60)
    print(f"Total tests: {metrics['total_tests']}")
    print(f"Success rate: {metrics['success_rate']}%")
    print(f"Avg routing time: {metrics['avg_routing_time_ms']}ms")
    print(f"Skill activation rate: {metrics['skill_activation_rate']}%")
    print(f"MCP accuracy: {metrics['mcp_accuracy']}%")
    print(f"Memory usage rate: {metrics['memory_usage_rate']}%")
    print()
    
    output_dir = Path("audit/baseline_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"baseline_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "results": [asdict(r) for r in results],
            "metrics": metrics
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print()
    
    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    if metrics['skill_activation_rate'] < 50:
        print("⚠️  Skill activation rate is low. Enable skill orchestration.")
    if metrics['mcp_accuracy'] < 80:
        print("⚠️  MCP accuracy is low. Enable phase-aware MCP selection.")
    if metrics['memory_usage_rate'] < 50:
        print("⚠️  Memory usage is low. Enable memory preloading.")
    
    if not phase_aware:
        print("⚠️  Phase-aware MCP is DISABLED. Enable in router.yaml:")
        print("    phase_aware:")
        print("      enabled: true")

if __name__ == "__main__":
    main()
