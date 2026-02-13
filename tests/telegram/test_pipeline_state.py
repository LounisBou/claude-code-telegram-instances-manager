"""Tests for PipelinePhase and PipelineState."""

from __future__ import annotations
from unittest.mock import MagicMock

from src.telegram.pipeline_state import PipelinePhase, PipelineState


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
