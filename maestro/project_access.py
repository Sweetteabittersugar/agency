"""Allowlist-based boundary for user-selected project paths."""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock


class ProjectAccessError(ValueError):
    code = "PROJECT_ROOT_REQUIRED"


class ProjectPathRejected(ProjectAccessError):
    code = "PROJECT_PATH_REJECTED"


_lock = RLock()
_allowed_roots: tuple[Path, ...] = ()


def _real_existing_directory(value: str | os.PathLike[str]) -> Path:
    path = Path(value).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ProjectPathRejected(f"project root does not exist: {path}") from exc
    if not resolved.is_dir():
        raise ProjectPathRejected(f"project root is not a directory: {resolved}")
    return resolved


def configure_project_roots(values: list[str] | tuple[str, ...]) -> tuple[Path, ...]:
    """Replace the process allowlist with canonical existing directories."""
    roots: list[Path] = []
    for value in values:
        resolved = _real_existing_directory(value)
        if resolved not in roots:
            roots.append(resolved)
    global _allowed_roots
    with _lock:
        _allowed_roots = tuple(roots)
    return _allowed_roots


def allowed_project_roots() -> tuple[Path, ...]:
    with _lock:
        return _allowed_roots


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(candidate), str(root))) == str(root)
    except ValueError:
        return False


def authorize_project_path(
    value: str | os.PathLike[str] | None,
    *,
    must_exist: bool = True,
    require_directory: bool = False,
) -> Path:
    """Resolve a path through links/junctions and require allowlist containment."""
    roots = allowed_project_roots()
    if not roots:
        raise ProjectAccessError(
            "project file operations are disabled; start Agency with --project-root PATH"
        )
    if value is None or not str(value).strip():
        if len(roots) == 1:
            return roots[0]
        raise ProjectPathRejected("a project path is required when multiple roots are allowed")

    path = Path(value).expanduser()
    try:
        resolved = path.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise ProjectPathRejected(f"project path cannot be resolved: {path}") from exc

    # Path.resolve follows Windows junctions and symlinks.  Resolving every
    # existing path at request time also closes links created after startup.
    if not any(_is_within(resolved, root) for root in roots):
        raise ProjectPathRejected("project path is outside the configured roots")
    if require_directory and (not resolved.exists() or not resolved.is_dir()):
        raise ProjectPathRejected("project path is not an existing directory")
    return resolved


def project_binding(value: str | os.PathLike[str] | None) -> str:
    """Return the canonical project directory used to bind a durable run."""
    return str(authorize_project_path(value, require_directory=True))
