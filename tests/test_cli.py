from __future__ import annotations

import sys

import pytest

from maestro import cli


def test_version_prints_only_version_without_starting_server(capsys):
    sys.modules.pop("maestro.flask_app", None)
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "0.5.0"
    assert "maestro.flask_app" not in sys.modules


def test_bare_command_displays_help_without_starting_server(capsys):
    sys.modules.pop("maestro.flask_app", None)
    assert cli.main([]) == 0
    assert "start" in capsys.readouterr().out
    assert "maestro.flask_app" not in sys.modules


def test_project_root_option_is_repeatable(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    args = cli.build_parser().parse_args(
        ["start", "--project-root", str(first), "--project-root", str(second)]
    )
    assert args.project_root == [str(first), str(second)]
