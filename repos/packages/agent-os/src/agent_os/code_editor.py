from __future__ import annotations

import subprocess
from pathlib import Path

from .contracts import CodeEditorInput, CodeEditorOutput


class CodeEditor:
    """MVP code editor contract adapter (verification-focused)."""

    def apply(self, edit_input: CodeEditorInput) -> CodeEditorOutput:
        repo_path = Path(edit_input.repo_path)
        verification: dict[str, dict[str, str | int]] = {}

        for cmd in edit_input.verify_commands:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            verification[cmd] = {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }

        return CodeEditorOutput(
            patch="",
            files_changed=edit_input.target_files,
            verification=verification,
        )
