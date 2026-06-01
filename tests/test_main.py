from __future__ import annotations

import subprocess
import sys


def test_module_main_invocation():
    result = subprocess.run(
        [sys.executable, "-m", "ssg", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ssg" in result.stdout
