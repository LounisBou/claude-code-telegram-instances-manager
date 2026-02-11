# tests/test_project_scanner.py
import logging

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


class TestScanProjectsLogging:
    def test_logs_root_and_count(self, tmp_projects, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        with caplog.at_level(logging.DEBUG, logger="src.project_scanner"):
            projects = scan_projects(str(tmp_projects))
        assert any("Scanning" in r.message for r in caplog.records)
        assert any("Found 2 projects" in r.message for r in caplog.records)

    def test_trace_logs_each_entry(self, tmp_projects, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        with caplog.at_level(TRACE, logger="src.project_scanner"):
            projects = scan_projects(str(tmp_projects))
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert len(trace_records) >= 2
