# tests/test_project_scanner.py
from src.project_scanner import scan_projects, Project


class TestScanProjects:
    def test_finds_git_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "project-alpha" in names

    def test_finds_claude_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "project-beta" in names

    def test_ignores_non_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "not-a-project" not in names

    def test_returns_absolute_paths(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        for p in projects:
            assert p.path.startswith("/")

    def test_returns_sorted_by_name(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert names == sorted(names)

    def test_empty_directory(self, tmp_path):
        projects = scan_projects(str(tmp_path))
        assert projects == []

    def test_nonexistent_directory(self):
        projects = scan_projects("/nonexistent/path")
        assert projects == []

    def test_ignores_hidden_directories(self, tmp_path):
        hidden = tmp_path / ".hidden-project"
        hidden.mkdir()
        (hidden / ".git").mkdir()
        projects = scan_projects(str(tmp_path))
        assert len(projects) == 0

    def test_scan_depth_one(self, tmp_path):
        nested = tmp_path / "parent" / "child"
        nested.mkdir(parents=True)
        (nested / ".git").mkdir()
        projects = scan_projects(str(tmp_path), depth=1)
        names = [p.name for p in projects]
        assert "child" not in names


class TestProject:
    def test_project_equality(self):
        p1 = Project(name="foo", path="/a/foo")
        p2 = Project(name="foo", path="/a/foo")
        assert p1 == p2

    def test_project_repr(self):
        p = Project(name="foo", path="/a/foo")
        assert "foo" in repr(p)
