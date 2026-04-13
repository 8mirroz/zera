from __future__ import annotations

import unittest


class PytestCompat:
    """Minimal fallback so unittest discovery can import pytest-style modules."""

    @staticmethod
    def skip(reason: str) -> None:
        raise unittest.SkipTest(reason)

    @staticmethod
    def main(*_: object, **__: object) -> int:
        raise SystemExit("pytest is required to run this pytest-style test module")


try:
    import pytest as pytest  # type: ignore[no-redef]
except ImportError:
    pytest = PytestCompat()
