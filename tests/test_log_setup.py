from __future__ import annotations

import logging
from unittest.mock import patch

from src.log_setup import TRACE, setup_logging


class TestTraceLevel:
    def test_trace_level_value(self):
        assert TRACE == 5

    def test_trace_level_name(self):
        assert logging.getLevelName(TRACE) == "TRACE"

    def test_logger_has_trace_method(self):
        setup_logging(debug=False, trace=False, verbose=False)
        logger = logging.getLogger("test.trace")
        assert hasattr(logger, "trace")
        assert callable(logger.trace)


class TestSetupLogging:
    def test_default_console_info(self):
        root = setup_logging(debug=False, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert len(console) == 1
        assert console[0].level == logging.INFO

    def test_debug_console_debug(self):
        root = setup_logging(debug=True, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == logging.DEBUG

    def test_trace_creates_file_handler(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            setup_logging(debug=False, trace=True, verbose=False)
        src_logger = logging.getLogger("src")
        file_handlers = [h for h in src_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].level == TRACE

    def test_trace_console_stays_debug(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            root = setup_logging(debug=False, trace=True, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == logging.DEBUG

    def test_trace_verbose_console_at_trace(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            root = setup_logging(debug=False, trace=True, verbose=True)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == TRACE

    def test_trace_file_naming(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            setup_logging(debug=False, trace=True, verbose=False)
        log_files = list(tmp_path.iterdir())
        assert len(log_files) == 1
        assert log_files[0].name.startswith("trace-")
        assert log_files[0].suffix == ".log"

    def test_no_file_without_trace(self):
        setup_logging(debug=True, trace=False, verbose=False)
        src_logger = logging.getLogger("src")
        file_handlers = [h for h in src_logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_src_logger_gets_debug_handler(self):
        """Regression: src.* loggers must inherit debug-level handler."""
        setup_logging(debug=True, trace=False, verbose=False)
        src_logger = logging.getLogger("src")
        console = [
            h for h in src_logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console) == 1
        assert console[0].level == logging.DEBUG

    def test_src_child_logger_inherits(self):
        """Module loggers like src.bot must propagate to the src handler."""
        setup_logging(debug=True, trace=False, verbose=False)
        child = logging.getLogger("src.bot")
        # child should propagate and use src's handlers
        assert child.propagate is True
        assert child.parent.name == "src"

    def test_idempotent_clears_old_handlers(self):
        setup_logging(debug=True, trace=False, verbose=False)
        root = setup_logging(debug=False, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert len(console) == 1
