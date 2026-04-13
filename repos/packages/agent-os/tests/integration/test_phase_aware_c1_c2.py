#!/usr/bin/env python3
"""Test phase-aware MCP for C1-C2 tasks"""
import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

ROOT = Path(__file__).resolve().parents[4]

@pytest.mark.skip(reason="phase_aware_override no longer in router.yaml — feature is default behavior")
def test_phase_aware_c1_c2():
    """Test that phase-aware is enabled for C1-C2"""

    config_path = ROOT / "configs/orchestrator/router.yaml"
    if not config_path.exists():
        pytest.skip(f"Router config not found: {config_path}")
    with open(config_path) as f:
        content = f.read()
    
    # Check C1
    assert "C1:" in content
    c1_section = content.split("C1:")[1].split("C2:")[0]
    assert "phase_aware_override: true" in c1_section, "C1 phase_aware_override should be true"
    
    # Check C2
    assert "C2:" in content
    c2_section = content.split("C2:")[1].split("C3:")[0]
    assert "phase_aware_override: true" in c2_section, "C2 phase_aware_override should be true"
    
    print("✓ Phase-aware enabled for C1")
    print("✓ Phase-aware enabled for C2")
    print("\nPhase 1 Complete: C1-C2 phase-aware MCP enabled")
    return True

if __name__ == "__main__":
    success = test_phase_aware_c1_c2()
    sys.exit(0 if success else 1)
