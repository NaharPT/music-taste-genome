"""Tests for temporal analyzer."""

import pytest
from src.analyzers.temporal_analyzer import (
    analyze_temporal_patterns,
    format_hour_timeline,
)


def _make_timestamped_track(hour, tempo=120.0, energy=0.7, valence=0.5):
    return {
        "id": f"t_{hour}",
        "name": f"Track at {hour}",
        "artists": ["Test"],
        "played_at": f"2026-02-10T{hour:02d}:30:00Z",
        "audio_features": {
            "tempo": tempo,
            "energy": energy,
            "valence": valence,
        },
    }


class TestAnalyzeTemporalPatterns:
    def test_empty_tracks(self):
        result = analyze_temporal_patterns([])
        assert result["total_tracks_with_timestamps"] == 0
        assert result["peak_hour"] is None

    def test_single_track(self):
        tracks = [_make_timestamped_track(14)]
        result = analyze_temporal_patterns(tracks)
        assert result["total_tracks_with_timestamps"] == 1
        assert result["peak_hour"] == 14
        assert result["hour_distribution"][14] == 1

    def test_morning_evening_split(self):
        morning_tracks = [
            _make_timestamped_track(8, tempo=110, energy=0.6, valence=0.4),
            _make_timestamped_track(9, tempo=115, energy=0.65, valence=0.45),
        ]
        evening_tracks = [
            _make_timestamped_track(20, tempo=130, energy=0.8, valence=0.6),
            _make_timestamped_track(21, tempo=135, energy=0.85, valence=0.65),
        ]
        result = analyze_temporal_patterns(morning_tracks + evening_tracks)

        assert result["morning_avg_features"] is not None
        assert result["evening_avg_features"] is not None
        assert result["morning_avg_features"]["tempo"] == 112.5
        assert result["evening_avg_features"]["tempo"] == 132.5

    def test_circadian_shift(self):
        tracks = [
            _make_timestamped_track(8, tempo=100, energy=0.5, valence=0.4),
            _make_timestamped_track(20, tempo=130, energy=0.8, valence=0.6),
        ]
        result = analyze_temporal_patterns(tracks)
        shift = result["circadian_shift"]
        assert shift is not None
        assert shift["tempo_delta"] == 30.0
        assert shift["energy_delta"] == 0.3
        assert shift["valence_delta"] == 0.2

    def test_no_morning_tracks(self):
        tracks = [_make_timestamped_track(20)]
        result = analyze_temporal_patterns(tracks)
        assert result["morning_avg_features"] is None
        assert result["circadian_shift"] is None

    def test_invalid_timestamps_skipped(self):
        tracks = [
            _make_timestamped_track(14),
            {"id": "bad", "name": "Bad", "artists": ["X"], "played_at": "not-a-date"},
        ]
        result = analyze_temporal_patterns(tracks)
        assert result["total_tracks_with_timestamps"] == 1

    def test_peak_hour_detection(self):
        # 3 tracks at hour 15, 1 at hour 10
        tracks = [
            _make_timestamped_track(15),
            _make_timestamped_track(15),
            _make_timestamped_track(15),
            _make_timestamped_track(10),
        ]
        # Fix duplicate timestamps
        tracks[1]["played_at"] = "2026-02-10T15:31:00Z"
        tracks[2]["played_at"] = "2026-02-10T15:32:00Z"

        result = analyze_temporal_patterns(tracks)
        assert result["peak_hour"] == 15


class TestFormatHourTimeline:
    def test_basic_format(self):
        dist = [0] * 24
        dist[14] = 5
        dist[15] = 3
        output = format_hour_timeline(dist)
        assert "14:00" in output
        assert "<< peak" in output

    def test_empty_distribution(self):
        dist = [0] * 24
        output = format_hour_timeline(dist)
        assert "00:00" in output

    def test_invalid_input(self):
        assert format_hour_timeline([]) == ""
        assert format_hour_timeline(None) == ""
