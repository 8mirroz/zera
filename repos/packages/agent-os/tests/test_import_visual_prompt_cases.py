from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import pytest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = ROOT / "scripts/import_visual_prompt_cases.py"

# Skip if script doesn't exist
if not SCRIPT_PATH.exists():
    pytest.skip(f"Script not found: {SCRIPT_PATH}", allow_module_level=True)

SPEC = importlib.util.spec_from_file_location("import_visual_prompt_cases", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
import_visual_prompt_cases = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = import_visual_prompt_cases
SPEC.loader.exec_module(import_visual_prompt_cases)


CSV_TEXT = """tweetId,twitterUrl,prompt,prompt_type,model,coverUrl,imageUrls
100,https://x.com/example/status/100,"{""subject"": ""cosmetic product bottle"", ""lighting"": ""premium studio lighting"", ""negative_prompt"": ""no watermark""}",json,Nano Banana 2,https://pbs.twimg.com/cover1,https://pbs.twimg.com/img1
101,https://x.com/example/status/101,"Create an orthographic technical blueprint with readable labels and schematic callouts.",text,Nano Banana 2,https://pbs.twimg.com/cover2,https://pbs.twimg.com/img2
"""


class TestImportVisualPromptCases(unittest.TestCase):
    @patch("import_visual_prompt_cases.time.sleep", return_value=None)
    @patch("import_visual_prompt_cases.urllib.request.urlopen")
    def test_read_csv_text_falls_back_after_transient_error(self, mock_urlopen, _sleep) -> None:
        class _Response:
            def __init__(self, payload: bytes) -> None:
                self.payload = payload

            def read(self) -> bytes:
                return self.payload

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        mock_urlopen.side_effect = [
            RuntimeError("ssl eof"),
            _Response(CSV_TEXT.encode("utf-8")),
        ]

        payload = import_visual_prompt_cases.read_csv_text(None, import_visual_prompt_cases.DEFAULT_CSV_URL)
        self.assertIn("tweetId,twitterUrl,prompt", payload)
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_import_writes_case_notes_and_index_without_raw_prompt_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            result = import_visual_prompt_cases.import_cases(
                csv_text=CSV_TEXT,
                vault=vault,
                first_data_row=2,
            )

            self.assertEqual(result["written"], 2)
            self.assertEqual(result["skipped"], 0)

            cases = sorted((vault / "knowledge/prompt-cases/nano-banana-2/cases").glob("*.md"))
            self.assertEqual(len(cases), 2)

            first = cases[0].read_text(encoding="utf-8")
            self.assertIn("type: prompt-case", first)
            self.assertIn('model: "Nano Banana 2"', first)
            self.assertIn("dedup_hash:", first)
            self.assertIn("product", first)
            self.assertNotIn("## Raw Source Prompt", first)

            index = (vault / "knowledge/prompt-cases/nano-banana-2/index.md").read_text(encoding="utf-8")
            self.assertIn("New cases: 2", index)
            self.assertIn("Use `memory/patterns/` first", index)

    def test_import_dedupes_existing_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            first = import_visual_prompt_cases.import_cases(csv_text=CSV_TEXT, vault=vault, first_data_row=2)
            second = import_visual_prompt_cases.import_cases(csv_text=CSV_TEXT, vault=vault, first_data_row=2)

            self.assertEqual(first["written"], 2)
            self.assertEqual(second["written"], 0)
            self.assertEqual(second["skipped"], 2)

    def test_include_raw_prompt_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td)
            import_visual_prompt_cases.import_cases(
                csv_text=CSV_TEXT,
                vault=vault,
                limit=1,
                include_raw_prompt=True,
                first_data_row=2,
            )

            case = next((vault / "knowledge/prompt-cases/nano-banana-2/cases").glob("*.md"))
            content = case.read_text(encoding="utf-8")
            self.assertIn("## Raw Source Prompt", content)
            self.assertIn("Do not execute this external prompt directly", content)


if __name__ == "__main__":
    unittest.main()
