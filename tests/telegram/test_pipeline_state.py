"""Tests for PipelinePhase, PipelineState, and helper functions."""

from __future__ import annotations
from unittest.mock import MagicMock

from src.telegram.pipeline_state import (
    PipelinePhase,
    PipelineState,
    is_tool_request_pending,
    mark_tool_acted,
)


class TestPipelinePhase:
    def test_dormant_exists(self):
        assert PipelinePhase.DORMANT.value == "dormant"

    def test_thinking_exists(self):
        assert PipelinePhase.THINKING.value == "thinking"

    def test_streaming_exists(self):
        assert PipelinePhase.STREAMING.value == "streaming"

    def test_tool_pending_exists(self):
        assert PipelinePhase.TOOL_PENDING.value == "tool_pending"


class TestPipelineState:
    def test_initial_phase_is_dormant(self):
        emu = MagicMock()
        streaming = MagicMock()
        ps = PipelineState(emulator=emu, streaming=streaming)
        assert ps.phase == PipelinePhase.DORMANT

    def test_has_emulator(self):
        emu = MagicMock()
        ps = PipelineState(emulator=emu, streaming=MagicMock())
        assert ps.emulator is emu

    def test_has_streaming(self):
        sm = MagicMock()
        ps = PipelineState(emulator=MagicMock(), streaming=sm)
        assert ps.streaming is sm

    def test_prev_view_is_none(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        assert ps.prev_view is None

    def test_tool_acted_is_false(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        assert ps.tool_acted is False


class TestMarkToolActed:
    def test_sets_tool_acted_true(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        assert ps.tool_acted is False
        mark_tool_acted(ps)
        assert ps.tool_acted is True

    def test_none_pipeline_is_noop(self):
        mark_tool_acted(None)  # should not raise

    def test_idempotent(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        mark_tool_acted(ps)
        mark_tool_acted(ps)
        assert ps.tool_acted is True


class TestIsToolRequestPending:
    def test_true_when_tool_pending_and_not_acted(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        ps.phase = PipelinePhase.TOOL_PENDING
        ps.tool_acted = False
        assert is_tool_request_pending(ps) is True

    def test_false_when_tool_acted(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        ps.phase = PipelinePhase.TOOL_PENDING
        ps.tool_acted = True
        assert is_tool_request_pending(ps) is False

    def test_false_when_not_tool_pending(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        ps.phase = PipelinePhase.STREAMING
        ps.tool_acted = False
        assert is_tool_request_pending(ps) is False

    def test_false_when_none(self):
        assert is_tool_request_pending(None) is False

    def test_false_when_dormant(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        ps.phase = PipelinePhase.DORMANT
        assert is_tool_request_pending(ps) is False
