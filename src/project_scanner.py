from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    """A discovered project with its display name and absolute path."""

    name: str
    path: str


def scan_projects(root: str, depth: int = 1) -> list[Project]:
    """Scan a directory for projects containing .git or .claude markers.

    Iterates over immediate subdirectories of the given root, skipping
    hidden directories (those starting with '.'), and collects entries
    that contain a .git or .claude directory.

    Args:
        root: Absolute or relative path to the parent directory to scan.
        depth: Scan depth (currently unused, reserved for future
            recursive scanning support).

    Returns:
        List of discovered projects sorted alphabetically by name.
        Returns an empty list if root is not an existing directory.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return []

    projects = []
    for entry in root_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if (entry / ".git").exists() or (entry / ".claude").exists():
            projects.append(Project(name=entry.name, path=str(entry.resolve())))

    projects.sort(key=lambda p: p.name)
    return projects
