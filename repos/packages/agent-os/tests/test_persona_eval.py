from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.persona_eval import PersonaEvalSuite


class TestPersonaEvalSuite(unittest.TestCase):
    def test_scores_actionable_grounded_response(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            path = repo / "configs/tooling/persona_eval_suite.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"thresholds":{"overall_min":0.8}}', encoding="utf-8")
            result = PersonaEvalSuite(repo).score(
                response_text="I may be wrong, so let's verify and turn this into a clear next step plan.",
                persona_version="zera-v1",
                mode="plan",
                meta={"selected_mode": "plan"},
            )
            self.assertTrue(result.passed)
            self.assertGreaterEqual(result.scores["anti_sycophancy"], 0.9)
            self.assertGreaterEqual(result.scores["actionability"], 0.85)


if __name__ == "__main__":
    unittest.main()
