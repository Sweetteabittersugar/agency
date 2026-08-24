from __future__ import annotations

import os
import subprocess
import sys

import pytest

from maestro.project_access import (
    ProjectAccessError,
    ProjectPathRejected,
    authorize_project_path,
    configure_project_roots,
)


@pytest.fixture(autouse=True)
def reset_roots():
    configure_project_roots([])
    yield
    configure_project_roots([])


def test_project_operations_require_an_explicit_root(tmp_path):
    with pytest.raises(ProjectAccessError, match="--project-root"):
        authorize_project_path(tmp_path)


def test_path_outside_root_is_rejected(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    configure_project_roots([str(allowed)])
    with pytest.raises(ProjectPathRejected, match="outside"):
        authorize_project_path(outside)


def test_symlink_or_junction_escape_is_rejected(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    link = allowed / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError as exc:
        if sys.platform != "win32":
            pytest.skip(f"directory links are unavailable: {exc}")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"directory junctions are unavailable: {result.stderr}")
    configure_project_roots([str(allowed)])
    with pytest.raises(ProjectPathRejected, match="outside"):
        authorize_project_path(link)
