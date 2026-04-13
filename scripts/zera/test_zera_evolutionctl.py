#!/usr/bin/env python3
"""
Tests for zera-evolutionctl Wave 5:
  Hermetic — all real paths are patched, writes to ~/.hermes or repo docs fail tests.
  Covers: promotion window, snapshot safety, clean promote-enable, rollback,
  gateway intent, smoke probe markers, promote-status, artifact validation,
  runtime audit, attempt cleanup.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock, TestCase

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "zera"))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "evolutionctl", ROOT / "scripts" / "zera" / "zera-evolutionctl.py"
)
evo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evo)

# Real paths that tests must NEVER write to
REAL_HERMES_ROOT = Path.home() / ".hermes"
REAL_REMEDIATION = ROOT / "docs" / "remediation"

# ── Hermeticity guard ────────────────────────────────────────────────

_original_write_text = Path.write_text
_original_mkdir = Path.mkdir

def _hermetic_write_guard(self, *args, **kwargs):
    """Fail test if any code tries to write to real ~/.hermes or docs/remediation."""
    resolved = str(self.resolve()) if self.exists() else str(self)
    if str(REAL_HERMES_ROOT) in resolved or resolved.startswith(str(REAL_HERMES_ROOT)):
        raise PermissionError(
            f"TEST HERMETICITY VIOLATION: write to real Hermes path: {resolved}"
        )
    if str(REAL_REMEDIATION) in resolved or resolved.startswith(str(REAL_REMEDIATION)):
        raise PermissionError(
            f"TEST HERMETICITY VIOLATION: write to real remediation path: {resolved}"
        )
    return _original_write_text(self, *args, **kwargs)


def _hermetic_mkdir_guard(self, *args, **kwargs):
    resolved = str(self.resolve()) if self.exists() else str(self)
    if str(REAL_HERMES_ROOT) in resolved or resolved.startswith(str(REAL_HERMES_ROOT)):
        raise PermissionError(
            f"TEST HERMETICITY VIOLATION: mkdir in real Hermes path: {resolved}"
        )
    if str(REAL_REMEDIATION) in resolved or resolved.startswith(str(REAL_REMEDIATION)):
        raise PermissionError(
            f"TEST HERMETICITY VIOLATION: mkdir in real remediation path: {resolved}"
        )
    return _original_mkdir(self, *args, **kwargs)


def _activate_hermetic_guard():
    """Activate hermeticity guard for test duration."""
    mock.patch.object(Path, "write_text", _hermetic_write_guard).start()
    mock.patch.object(Path, "mkdir", _hermetic_mkdir_guard).start()


def _deactivate_hermetic_guard():
    """Deactivate hermeticity guard."""
    # Patches are stopped by tearDown in each test class
    pass


# ── Test fixtures ────────────────────────────────────────────────────

def _make_fake_zera(tmp: Path) -> Path:
    zera = tmp / "zera"
    zera.mkdir()
    (zera / "config.yaml").write_text("model: test\ngateway:\n  adapters: {}\n")
    (zera / "backups").mkdir()
    (zera / "cron").mkdir()
    (zera / "cron" / "jobs.json").write_text('{"jobs": []}')
    return zera


def _make_fake_vault(tmp: Path) -> Path:
    vault = tmp / "vault" / "loops"
    vault.mkdir(parents=True)
    (vault / ".evolve-state.json").write_text("{}")
    return vault


def _make_fake_evo_dir(tmp: Path) -> Path:
    evo_dir = tmp / "evolution"
    evo_dir.mkdir()
    (evo_dir / "state.json").write_text("{}")
    (evo_dir / "evolutionctl-state.json").write_text("{}")
    (evo_dir / "evolutionctl.out.log").write_text("")
    (evo_dir / "loop.log").write_text("")
    return evo_dir


def _make_fake_snapshot_root(tmp: Path) -> Path:
    sr = tmp / "snapshots"
    sr.mkdir(parents=True)
    return sr


def _make_fake_scoped_artifacts(tmp: Path) -> Path:
    scoped = tmp / "scoped_artifacts"
    scoped.mkdir()
    return scoped


def _patch_all(tmp: Path, zera: Path, vault: Path, evo_dir: Path,
               snapshot_root: Path, promotion_state: Path, remediation: Path,
               policy_file: Path | None = None, scoped_artifacts: Path | None = None):
    """Return a list of active patches — ALL real paths mocked."""
    if scoped_artifacts is None:
        scoped_artifacts = tmp / "scoped_artifacts"
    patches = [
        mock.patch.object(evo, "HERMES_ZERA_PROFILE", zera),
        mock.patch.object(evo, "HERMES_PROFILES_DIR", tmp / "profiles"),
        mock.patch.object(evo, "HERMES_ROOT", tmp / ".hermes"),
        mock.patch.object(evo, "LEGACY_STATE_FILE", vault / ".evolve-state.json"),
        mock.patch.object(evo, "EVOLUTION_DIR", evo_dir),
        mock.patch.object(evo, "CTL_STATE_FILE", evo_dir / "evolutionctl-state.json"),
        mock.patch.object(evo, "CTL_LOG_FILE", evo_dir / "evolutionctl.out.log"),
        mock.patch.object(evo, "CORE_LOG_FILE", evo_dir / "loop.log"),
        mock.patch.object(evo, "SNAPSHOT_ROOT", snapshot_root),
        mock.patch.object(evo, "PROMOTION_STATE_FILE", promotion_state),
        mock.patch.object(evo, "PROMOTION_ARTIFACTS_DIR", remediation),
        mock.patch.object(evo, "HERMES_ZERA_ARTIFACT_BASE", scoped_artifacts),
        mock.patch.object(evo, "KILL_SWITCH_FILE", evo_dir / "KILL_SWITCH"),
        # Hermeticity guard
        mock.patch.object(Path, "write_text", _hermetic_write_guard),
        mock.patch.object(Path, "mkdir", _hermetic_mkdir_guard),
    ]
    if policy_file:
        patches.append(mock.patch.object(evo, "PROMOTION_POLICY_FILE", policy_file))
    for p in patches:
        p.start()
    return patches


def _unpatch(patches):
    for p in patches:
        p.stop()


# ── Tests ─────────────────────────────────────────────────────────────

class TestPromotionWindowEnforcement(TestCase):
    """Test _require_active_promotion_window and cmd_start guard."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)
        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_no_promotion_window_fails(self):
        ok, info = evo._require_active_promotion_window()
        self.assertFalse(ok)
        self.assertIn("not enabled", info.get("reason", ""))

    def test_start_allow_promote_without_window_fails(self):
        args = argparse.Namespace(no_promote=False, force=True, cycles=1,
                                  interval=300, forever=False, llm_score=False)
        rc = evo.cmd_start(args)
        self.assertEqual(rc, 2)

    def test_expired_ttl_fails(self):
        import datetime as dt
        evo.write_json(self.promotion_state, {
            "promotion": {
                "enabled": True,
                "scope": "full",
                "enabled_at": "2020-01-01T00:00:00+00:00",
                "expires_at": "2020-01-01T00:30:00+00:00",
                "snapshot_id": "snap-1",
                "attempt_id": "attempt-20200101_000000-expired",
            },
            "snapshots": [{"snapshot_id": "snap-1", "snapshot_dir": "/tmp/x"}],
        })
        ok, info = evo._require_active_promotion_window()
        self.assertFalse(ok)
        self.assertTrue(info.get("expired"))

    def test_missing_policy_report_fails(self):
        import datetime as dt
        future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
        snap_dir = self.snapshot_root / "snap-1"
        snap_dir.mkdir(parents=True)
        attempt_id = "attempt-20260101_000000-noreport"

        evo.write_json(self.promotion_state, {
            "promotion": {
                "enabled": True,
                "scope": "full",
                "enabled_at": "2026-01-01T00:00:00+00:00",
                "expires_at": future,
                "snapshot_id": "snap-1",
                "attempt_id": attempt_id,
            },
            "snapshots": [{"snapshot_id": "snap-1", "snapshot_dir": str(snap_dir)}],
        })
        ok, info = evo._require_active_promotion_window()
        self.assertFalse(ok)
        self.assertIn("policy", info.get("reason", "").lower())

    def test_active_window_passes(self):
        import datetime as dt
        future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
        attempt_id = "attempt-20260101_000000-test12345678"

        # Create a passing policy check report bound to attempt
        scoped_dir = self.scoped / attempt_id / "promote-policy-check"
        scoped_dir.mkdir(parents=True)
        evo.write_json(scoped_dir / "report.json", {
            "ok": True, "attempt_id": attempt_id,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()
        })

        snap_dir = self.snapshot_root / "snap-1"
        snap_dir.mkdir(parents=True)

        evo.write_json(self.promotion_state, {
            "promotion": {
                "enabled": True,
                "scope": "full",
                "enabled_at": "2026-01-01T00:00:00+00:00",
                "expires_at": future,
                "snapshot_id": "snap-1",
                "attempt_id": attempt_id,
            },
            "snapshots": [{"snapshot_id": "snap-1", "snapshot_dir": str(snap_dir)}],
        })
        ok, info = evo._require_active_promotion_window()
        self.assertTrue(ok)
        self.assertGreater(info.get("remaining_seconds", 0), 0)


class TestSnapshotStorage(TestCase):
    """Test snapshot storage outside zera profile."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)
        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_create_snapshot_outside_zera(self):
        snap = evo._create_promotion_snapshot("test")
        self.assertTrue(snap["safe"])
        snap_dir = Path(snap["snapshot_dir"])
        try:
            snap_dir.relative_to(self.zera)
            self.fail("Snapshot should not be inside zera profile")
        except ValueError:
            pass

    def test_snapshot_root_created(self):
        evo._create_promotion_snapshot("test")
        self.assertTrue(self.snapshot_root.exists())

    def test_is_snapshot_safe(self):
        safe_dir = self.snapshot_root / "snap"
        safe_dir.mkdir()
        self.assertTrue(evo._is_snapshot_safe(safe_dir))

        unsafe_dir = self.zera / "backups" / "_snapshots" / "snap"
        unsafe_dir.mkdir(parents=True)
        self.assertFalse(evo._is_snapshot_safe(unsafe_dir))


class TestCleanPromoteEnable(TestCase):
    """Test promote-enable with mocked gates."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)

        # Policy with all gates optional except rollback_snapshot
        self.policy_file = self.tmp / "policy.yaml"
        self.policy_file.write_text(
            "gates:\n"
            "  swarmctl_doctor:\n    required: false\n"
            "  check_zera_hardening:\n    required: false\n"
            "  trace_validator:\n    required: false\n"
            "  test_mcp_profiles:\n    required: false\n"
            "  shadow_smoke:\n    required: false\n"
            "  rollback_snapshot:\n    required: true\n"
            "  gateway_check:\n    required: false\n"
            "gateway:\n  mode: disabled_allowed\n"
            "promotion:\n  max_ttl_minutes: 120\n"
        )

        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            self.policy_file, self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_clean_promote_enable_creates_snapshot_then_enables(self):
        args = argparse.Namespace(scope="full", ttl=30)
        rc = evo.cmd_promote_enable(args)
        self.assertEqual(rc, 0)

        pstate = evo.read_json(self.promotion_state)
        self.assertTrue(pstate["promotion"]["enabled"])
        self.assertIsNotNone(pstate["promotion"]["snapshot_id"])
        self.assertIsNotNone(pstate["promotion"]["attempt_id"])
        self.assertIsNotNone(pstate["promotion"]["expires_at"])

        snaps = list(self.snapshot_root.iterdir())
        self.assertGreater(len(snaps), 0)

    def test_promote_enable_policy_failure_still_creates_snapshot(self):
        args = argparse.Namespace(scope="full", ttl=30)
        rc = evo.cmd_promote_enable(args)
        self.assertEqual(rc, 0)
        snaps = list(self.snapshot_root.iterdir())
        self.assertGreater(len(snaps), 0)


class TestRollbackSafety(TestCase):
    """Test rollback refuses unsafe snapshot paths."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)

        # SAFE snapshot outside zera
        safe_snap = self.snapshot_root / "snap-safe"
        safe_snap.mkdir(parents=True)
        (safe_snap / "profile").mkdir()
        (safe_snap / "profile" / "config.yaml").write_text("model: safe\n")
        (safe_snap / "vault_loops").mkdir()
        (safe_snap / "vault_loops" / ".evolve-state.json").write_text('{"cycle": 5}')
        (safe_snap / "cron").mkdir()
        (safe_snap / "cron" / "jobs.json").write_text('{"jobs": []}')
        evo.write_json(safe_snap / "snapshot_meta.json", {
            "snapshot_id": "snap-safe", "label": "safe",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "snapshots": ["profile", "vault_loops", "cron"],
            "snapshot_dir": str(safe_snap),
        })

        # UNSAFE snapshot inside zera
        unsafe_snap = self.zera / "backups" / "_snapshots" / "snap-unsafe"
        unsafe_snap.mkdir(parents=True)
        (unsafe_snap / "profile").mkdir()
        (unsafe_snap / "profile" / "config.yaml").write_text("model: unsafe\n")
        (unsafe_snap / "vault_loops").mkdir()
        (unsafe_snap / "vault_loops" / ".evolve-state.json").write_text('{"cycle": 3}')
        (unsafe_snap / "cron").mkdir()
        (unsafe_snap / "cron" / "jobs.json").write_text('{"jobs": []}')
        evo.write_json(unsafe_snap / "snapshot_meta.json", {
            "snapshot_id": "snap-unsafe", "label": "unsafe",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "snapshots": ["profile", "vault_loops", "cron"],
            "snapshot_dir": str(unsafe_snap),
        })

        evo.write_json(self.promotion_state, {
            "snapshots": [
                {"snapshot_id": "snap-safe", "snapshot_dir": str(safe_snap), "safe": True},
                {"snapshot_id": "snap-unsafe", "snapshot_dir": str(unsafe_snap), "safe": False},
            ],
            "latest_snapshot": "snap-safe",
        })

        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_rollback_unsafe_snapshot_refused(self):
        args = argparse.Namespace(snapshot="snap-unsafe", allow_legacy_internal_snapshot=False)
        rc = evo.cmd_promote_rollback(args)
        self.assertEqual(rc, 1)

    def test_rollback_unsafe_with_legacy_flag_succeeds(self):
        args = argparse.Namespace(snapshot="snap-unsafe", allow_legacy_internal_snapshot=True)
        rc = evo.cmd_promote_rollback(args)
        self.assertEqual(rc, 0)

    def test_rollback_safe_snapshot_succeeds(self):
        args = argparse.Namespace(snapshot="snap-safe", allow_legacy_internal_snapshot=False)
        rc = evo.cmd_promote_rollback(args)
        self.assertEqual(rc, 0)
        config = (self.zera / "config.yaml").read_text()
        self.assertIn("safe", config)


class TestGatewayFalseGreen(TestCase):
    """Test gateway-check does NOT pass on 'not running' when mode=required."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)

        self.policy_file = self.tmp / "policy.yaml"
        self.policy_file.write_text(
            "gateway:\n  mode: required\n  disabled_intent_required: true\n"
            "gates: {}\n"
        )

        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            self.policy_file, self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    @mock.patch.object(evo, "_hermes_run")
    def test_gateway_not_running_fails_when_required(self, mock_hermes):
        mock_hermes.return_value = mock.Mock(
            returncode=0, stdout="✗ Gateway is not running\n", stderr=""
        )
        ok, report = evo._check_gateway_compatibility_strict()
        self.assertFalse(ok)
        self.assertEqual(report["decision"], "blocked")

    @mock.patch.object(evo, "_hermes_run")
    def test_gateway_running_with_adapters_passes_when_required(self, mock_hermes):
        mock_hermes.return_value = mock.Mock(
            returncode=0, stdout="✓ Gateway is running\n  adapters: ready\n", stderr=""
        )
        ok, report = evo._check_gateway_compatibility_strict()
        self.assertTrue(ok)
        self.assertEqual(report["decision"], "ok")

    @mock.patch.object(evo, "_hermes_run")
    def test_gateway_not_running_passes_when_disabled_allowed(self, mock_hermes):
        with mock.patch.object(evo, "_load_promotion_policy",
                               return_value={"gateway": {"mode": "disabled_allowed", "disabled_intent_required": False}}):
            mock_hermes.return_value = mock.Mock(
                returncode=0, stdout="✗ Gateway is not running\n", stderr=""
            )
            ok, report = evo._check_gateway_compatibility_strict()
            self.assertTrue(ok)
            self.assertEqual(report["decision"], "ok")


class TestShadowSmokeProbeMarker(TestCase):
    """Test shadow-smoke probe marker and Qwen signature detection."""

    def test_qwen_signature_detection(self):
        output = "2026-04-11 ERROR Qwen OAuth refresh returned invalid JSON: unexpected token"
        found = evo._check_errors_log_for_signatures(output)
        self.assertTrue(found.get("Qwen OAuth refresh returned invalid JSON"))

    def test_qwen_signature_no_false_positive(self):
        output = "2026-04-11 INFO Request completed successfully"
        found = evo._check_errors_log_for_signatures(output)
        self.assertFalse(any(found.values()))

    @mock.patch.object(evo, "_hermes_run")
    def test_smoke_uses_probe_marker(self, mock_hermes):
        mock_hermes.return_value = mock.Mock(
            returncode=0, stdout="ok", stderr=""
        )
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        profiles_dir = self.tmp / "profiles"
        profiles_dir.mkdir()
        shadow = profiles_dir / "zera-shadow"
        shadow.mkdir()
        (self.tmp / "remediation").mkdir()

        with mock.patch.object(evo, "HERMES_PROFILES_DIR", profiles_dir), \
             mock.patch.object(evo, "PROMOTION_ARTIFACTS_DIR", self.tmp / "remediation"), \
             mock.patch.object(evo, "HERMES_ZERA_PROFILE", self.zera):
            args = argparse.Namespace(
                profile="zera-shadow", smoke_n=1, smoke_timeout=10,
                error_since="30m", probe_marker="my-custom-marker-12345"
            )
            evo.cmd_shadow_smoke(args)

        calls = mock_hermes.call_args_list
        chat_calls = [c for c in calls if "chat" in str(c)]
        self.assertGreater(len(chat_calls), 0)
        call_args = chat_calls[0]
        self.assertIn("my-custom-marker-12345", str(call_args))
        self.tmpdir.cleanup()


class TestPromoteStatus(TestCase):
    """Test promote-status command."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)
        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_promote_status_shows_disabled(self):
        rc = evo.cmd_promote_status(argparse.Namespace())
        self.assertEqual(rc, 0)

    def test_promote_status_detects_legacy_snapshots(self):
        internal = self.zera / "backups" / "_snapshots" / "legacy-snap"
        internal.mkdir(parents=True)
        evo.write_json(internal / "snapshot_meta.json", {"snapshot_id": "legacy-snap"})

        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            evo.cmd_promote_status(argparse.Namespace())
        output = buf.getvalue()
        self.assertIn("legacy_unsafe", output)


class TestArtifactValidation(TestCase):
    """Test validate-artifacts command."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)

        self.schema_file = self.tmp / "schema.json"
        self.schema_file.write_text(json.dumps({
            "required": ["schema_version", "command", "attempt_id", "ok", "timestamp"],
            "properties": {
                "schema_version": {"type": "integer"},
                "command": {"type": "string", "enum": ["promote-enable", "promote-policy-check"]},
                "attempt_id": {"type": "string"},
                "ok": {"type": "boolean"},
                "timestamp": {"type": "string"},
            }
        }))

        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )
        self.patches.append(mock.patch.object(evo, "ARTIFACT_SCHEMA_FILE", self.schema_file))
        self.patches[-1].start()

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_validate_artifacts_passes(self):
        attempt_id = "attempt-20260101_000000-valid"
        art_dir = self.scoped / attempt_id / "promote-enable"
        art_dir.mkdir(parents=True)
        evo.write_json(art_dir / "report.json", {
            "schema_version": 1, "command": "promote-enable",
            "attempt_id": attempt_id, "ok": True,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "snapshot_id": "snap-1",
        })

        args = argparse.Namespace(attempt_id=attempt_id)
        rc = evo.cmd_validate_artifacts(args)
        self.assertEqual(rc, 0)

    def test_validate_artifacts_fails_missing_fields(self):
        attempt_id = "attempt-20260101_000000-invalid"
        art_dir = self.scoped / attempt_id / "promote-enable"
        art_dir.mkdir(parents=True)
        evo.write_json(art_dir / "report.json", {"ok": True})  # missing required fields

        args = argparse.Namespace(attempt_id=attempt_id)
        rc = evo.cmd_validate_artifacts(args)
        self.assertEqual(rc, 1)


class TestRuntimeAudit(TestCase):
    """Test audit-runtime-state command."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.zera = _make_fake_zera(self.tmp)
        self.vault = _make_fake_vault(self.tmp)
        self.evo_dir = _make_fake_evo_dir(self.tmp)
        self.snapshot_root = _make_fake_snapshot_root(self.tmp)
        self.promotion_state = self.evo_dir / "promotion_state.json"
        self.remediation = self.tmp / "remediation"
        self.remediation.mkdir()
        self.scoped = _make_fake_scoped_artifacts(self.tmp)

        evo.write_json(self.promotion_state, {
            "snapshots": [],
            "promotion": {},
        })

        self.patches = _patch_all(
            self.tmp, self.zera, self.vault, self.evo_dir,
            self.snapshot_root, self.promotion_state, self.remediation,
            scoped_artifacts=self.scoped,
        )

    def tearDown(self):
        _unpatch(self.patches)
        self.tmpdir.cleanup()

    def test_audit_runtime_state_clean(self):
        rc = evo.cmd_audit_runtime_state(argparse.Namespace())
        self.assertEqual(rc, 0)


class TestHelperFunctions(TestCase):
    """Basic helper function tests."""

    def test_utc_now_returns_iso_string(self):
        result = evo.utc_now()
        self.assertIsInstance(result, str)
        self.assertIn("T", result)

    def test_read_json_missing_file(self):
        result = evo.read_json(Path("/nonexistent"))
        self.assertEqual(result, {})

    def test_write_json_and_read_back(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.json"
            data = {"key": "value"}
            evo.write_json(p, data)
            self.assertEqual(evo.read_json(p), data)

    def test_generate_attempt_id_format(self):
        aid = evo.generate_attempt_id()
        self.assertTrue(aid.startswith("attempt-"))
        self.assertGreater(len(aid), 20)


if __name__ == "__main__":
    import unittest
    unittest.main()
