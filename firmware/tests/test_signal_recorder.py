"""Tests for Sub-GHz signal recorder/player helpers."""

from collections import deque

from radio.signal_player import SignalPlayer
from radio.signal_recorder import SignalRecorder
from radio.sub_file import SubFile
from tests.mocks.mock_badge import MockBadge


def test_sub_file_roundtrip(tmp_path):
    path = tmp_path / "capture.sub"
    packets = [
        {"ts_ms": 0, "data": b"\xaa\xbb"},
        {"ts_ms": 150, "data": b"\x11\x22\x33"},
    ]
    SubFile.write(str(path), 915.0, "OOK", packets)

    loaded = SubFile.read(str(path))
    assert loaded["frequency_mhz"] == 915.0
    assert loaded["modulation"] == "OOK"
    assert len(loaded["packets"]) == 2
    assert loaded["packets"][0]["data"] == b"\xaa\xbb"


def test_signal_record_and_replay(tmp_path):
    badge = MockBadge()
    badge.lora._ook_rx_queue = deque([b"\xaa\xbb", b"\x01\x02\x03"])

    out_file = tmp_path / "test.sub"
    recorder = SignalRecorder(badge.lora)
    player = SignalPlayer(badge.lora)

    count = recorder.record(433.92, 0.25, str(out_file))
    assert count >= 1

    sent = player.replay(str(out_file), repeat=1, frequency_mhz=433.92)
    assert sent >= 1
    assert getattr(badge.lora, "_ook_tx_log", None)
