from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib import error as urllib_error

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.contracts import MemoryStoreInput
from agent_os.memory_store import MemoryStore

_ENV_KEYS = [
    "MEMORY_FILE_PATH",
    "MEMORY_BACKEND",
    "MEMU_API_KEY",
    "MEMU_BASE_URL",
    "MEMU_USER_ID",
    "MEMU_AGENT_ID",
    "MEMU_HTTP_TIMEOUT_SECONDS",
    "MEMU_FAIL_OPEN",
]


class _FakeHTTPResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class TestMemoryStoreMemUCloud(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _set_env(self, **values: str) -> None:
        for key in _ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in values.items():
            os.environ[key] = value

    def test_default_jsonl_behavior_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._set_env(MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"))
            with mock.patch("agent_os.memory_store.urllib_request.urlopen") as mock_urlopen:
                mem = MemoryStore(ROOT)
                write_out = mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                read_out = mem.operate(MemoryStoreInput(op="read", key="unit:test", payload={}))
                search_out = mem.operate(MemoryStoreInput(op="search", key="world", payload={}))

            self.assertNotIn("_backend", write_out.result)
            self.assertNotIn("_memu", write_out.result)
            self.assertGreaterEqual(len(read_out.result.get("items", [])), 1)
            self.assertGreaterEqual(len(search_out.result.get("items", [])), 1)
            self.assertEqual(search_out.confidence, 0.8)
            self.assertNotIn("_backend", search_out.result)
            mock_urlopen.assert_not_called()

    def test_memu_cloud_backend_without_api_key_falls_back_when_fail_open(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_FAIL_OPEN="true",
            )
            with mock.patch("agent_os.memory_store.urllib_request.urlopen") as mock_urlopen:
                mem = MemoryStore(ROOT)
                write_out = mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                search_out = mem.operate(MemoryStoreInput(op="search", key="world", payload={}))

            self.assertNotIn("_memu", write_out.result)
            self.assertNotIn("_backend", search_out.result)
            self.assertEqual(search_out.confidence, 0.8)
            mock_urlopen.assert_not_called()

    def test_memu_cloud_backend_without_api_key_raises_when_fail_open_false(self) -> None:
        self._set_env(MEMORY_BACKEND="memu_cloud", MEMU_FAIL_OPEN="false")
        with self.assertRaises(ValueError):
            MemoryStore(ROOT)

    def test_memu_write_local_success_and_memu_submitted(self) -> None:
        captured: list[tuple[str, dict]] = []

        def _fake_urlopen(req, timeout=0):
            payload = json.loads(req.data.decode("utf-8"))
            captured.append((req.full_url, payload))
            return _FakeHTTPResponse({"task_id": "t123"})

        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="true",
            )
            with mock.patch("agent_os.memory_store.urllib_request.urlopen", side_effect=_fake_urlopen):
                mem = MemoryStore(ROOT)
                out = mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))

        self.assertEqual(out.result.get("_backend"), "memu_cloud_hybrid")
        self.assertEqual(out.result.get("_memu", {}).get("status"), "submitted")
        self.assertEqual(out.result.get("_memu", {}).get("task_id"), "t123")
        self.assertEqual(len(captured), 1)
        self.assertTrue(captured[0][0].endswith("/api/v3/memory/memorize"))
        conversation = captured[0][1]["conversation"]
        self.assertEqual(len(conversation), 1)
        content = conversation[0]["content"]
        self.assertIn("AGENT_OS_MEMORY_RECORD_V1", content)
        self.assertIn("key=unit:test", content)
        self.assertIn('payload_json={"hello": "world"}', content)

    def test_memu_write_network_error_keeps_local_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            memfile = Path(td) / "memory.jsonl"
            self._set_env(
                MEMORY_FILE_PATH=str(memfile),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="false",
            )
            with mock.patch(
                "agent_os.memory_store.urllib_request.urlopen",
                side_effect=urllib_error.URLError("boom"),
            ):
                mem = MemoryStore(ROOT)
                out = mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
            file_content = memfile.read_text(encoding="utf-8")

        self.assertEqual(out.result.get("_backend"), "memu_cloud_hybrid")
        self.assertEqual(out.result.get("_memu", {}).get("status"), "failed")
        self.assertIn("boom", out.result.get("_memu", {}).get("error", ""))
        self.assertIn('"key": "unit:test"', file_content)

    def test_memu_search_merges_local_and_cloud_results(self) -> None:
        responses = iter(
            [
                _FakeHTTPResponse({"task_id": "t1"}),
                _FakeHTTPResponse({"items": [{"id": "cloud-1", "summary": "cloud hit"}]}),
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="true",
            )
            with mock.patch("agent_os.memory_store.urllib_request.urlopen", side_effect=lambda *a, **k: next(responses)):
                mem = MemoryStore(ROOT)
                mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                out = mem.operate(MemoryStoreInput(op="search", key="world", payload={}))

        items = out.result.get("items", [])
        self.assertGreaterEqual(len(items), 2)
        sources = {item.get("_source") for item in items}
        self.assertIn("jsonl_local", sources)
        self.assertIn("memu_cloud", sources)
        self.assertEqual(out.result.get("_backend"), "memu_cloud_hybrid")
        self.assertEqual(out.result.get("_memu", {}).get("status"), "ok")
        self.assertEqual(out.result.get("_memu", {}).get("hit_count"), 1)
        self.assertEqual(out.confidence, 0.9)
        self.assertIn("cloud-1", out.memory_ids)

    def test_memu_search_fallbacks_to_local_on_cloud_error_when_fail_open_true(self) -> None:
        responses = iter([
            _FakeHTTPResponse({"task_id": "t1"}),
            urllib_error.URLError("search-down"),
        ])

        def _side_effect(*args, **kwargs):
            value = next(responses)
            if isinstance(value, Exception):
                raise value
            return value

        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="true",
            )
            with mock.patch("agent_os.memory_store.urllib_request.urlopen", side_effect=_side_effect):
                mem = MemoryStore(ROOT)
                mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                out = mem.operate(MemoryStoreInput(op="search", key="world", payload={}))

        self.assertEqual(out.confidence, 0.8)
        self.assertEqual(out.result.get("_backend"), "memu_cloud_hybrid")
        self.assertEqual(out.result.get("_memu", {}).get("status"), "failed")
        items = out.result.get("items", [])
        self.assertTrue(items)
        self.assertTrue(all(item.get("_source") == "jsonl_local" for item in items))

    def test_memu_search_raises_on_cloud_error_when_fail_open_false(self) -> None:
        responses = iter([
            _FakeHTTPResponse({"task_id": "t1"}),
            urllib_error.URLError("search-down"),
        ])

        def _side_effect(*args, **kwargs):
            value = next(responses)
            if isinstance(value, Exception):
                raise value
            return value

        with tempfile.TemporaryDirectory() as td:
            self._set_env(
                MEMORY_FILE_PATH=str(Path(td) / "memory.jsonl"),
                MEMORY_BACKEND="memu_cloud",
                MEMU_API_KEY="test-key",
                MEMU_FAIL_OPEN="false",
            )
            with mock.patch("agent_os.memory_store.urllib_request.urlopen", side_effect=_side_effect):
                mem = MemoryStore(ROOT)
                mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                with self.assertRaises(RuntimeError):
                    mem.operate(MemoryStoreInput(op="search", key="world", payload={}))


if __name__ == "__main__":
    unittest.main()
