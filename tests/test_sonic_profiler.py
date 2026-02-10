"""Tests for sonic DNA profiler."""

import pytest
from src.analyzers.sonic_profiler import (
    aggregate_audio_features,
    compute_diversity_index,
    classify_dimension,
    build_signature,
    build_sonic_dna,
)


def _make_track(
    track_id="t1",
    artist="Artist",
    tempo=120.0,
    energy=0.7,
    valence=0.5,
    danceability=0.6,
    acousticness=0.3,
    instrumentalness=0.05,
    loudness=-6.0,
    speechiness=0.04,
    liveness=0.1,
    key=5,
    mode=1,
    duration_ms=210000,
):
    return {
        "id": track_id,
        "name": f"Track {track_id}",
        "artists": [artist],
        "audio_features": {
            "tempo": tempo,
            "energy": energy,
            "valence": valence,
            "danceability": danceability,
            "acousticness": acousticness,
            "instrumentalness": instrumentalness,
            "loudness": loudness,
            "speechiness": speechiness,
            "liveness": liveness,
            "key": key,
            "mode": mode,
            "duration_ms": duration_ms,
        },
    }


class TestAggregateAudioFeatures:
    def test_empty_tracks(self):
        assert aggregate_audio_features([]) == {}

    def test_single_track(self):
        tracks = [_make_track(tempo=120, energy=0.7, valence=0.5)]
        result = aggregate_audio_features(tracks)
        assert result["tempo"]["mean"] == 120.0
        assert result["tempo"]["median"] == 120.0
        assert result["energy"]["mean"] == 0.7
        assert result["valence"]["mean"] == 0.5

    def test_multiple_tracks_stats(self):
        tracks = [
            _make_track(track_id="t1", tempo=100, energy=0.5, valence=0.3),
            _make_track(track_id="t2", tempo=120, energy=0.7, valence=0.5),
            _make_track(track_id="t3", tempo=140, energy=0.9, valence=0.7),
        ]
        result = aggregate_audio_features(tracks)
        assert result["tempo"]["mean"] == 120.0
        assert result["tempo"]["median"] == 120.0
        assert result["tempo"]["min"] == 100.0
        assert result["tempo"]["max"] == 140.0
        assert result["energy"]["mean"] == 0.7

    def test_key_distribution(self):
        tracks = [
            _make_track(track_id="t1", key=0),  # C
            _make_track(track_id="t2", key=0),  # C
            _make_track(track_id="t3", key=5),  # F
            _make_track(track_id="t4", key=7),  # G
        ]
        result = aggregate_audio_features(tracks)
        assert result["key_distribution"]["C"] == 0.5
        assert result["key_distribution"]["F"] == 0.25
        assert result["key_distribution"]["G"] == 0.25

    def test_mode_split(self):
        tracks = [
            _make_track(track_id="t1", mode=1),
            _make_track(track_id="t2", mode=1),
            _make_track(track_id="t3", mode=0),
        ]
        result = aggregate_audio_features(tracks)
        assert result["mode_split"]["major"] == 0.67
        assert result["mode_split"]["minor"] == 0.33

    def test_low_valence_pct(self):
        tracks = [
            _make_track(track_id="t1", valence=0.2),   # low
            _make_track(track_id="t2", valence=0.1),   # low
            _make_track(track_id="t3", valence=0.5),   # not low
            _make_track(track_id="t4", valence=0.8),   # not low
        ]
        result = aggregate_audio_features(tracks)
        assert result["low_valence_pct"] == 50.0

    def test_tracks_without_features_skipped(self):
        tracks = [
            _make_track(track_id="t1", tempo=120),
            {"id": "t2", "name": "No features", "artists": ["X"], "audio_features": {}},
        ]
        result = aggregate_audio_features(tracks)
        assert result["tempo"]["mean"] == 120.0


class TestComputeDiversityIndex:
    def test_empty_tracks(self):
        result = compute_diversity_index([])
        assert result["diversity_index"] == 0

    def test_single_artist_low_diversity(self):
        tracks = [_make_track(track_id=f"t{i}", artist="Same") for i in range(10)]
        result = compute_diversity_index(tracks)
        # Single artist -> 0 entropy
        assert result["artist_entropy_normalized"] == 0.0

    def test_varied_artists_higher_diversity(self):
        tracks = [_make_track(track_id=f"t{i}", artist=f"Artist{i}") for i in range(10)]
        result = compute_diversity_index(tracks)
        assert result["artist_entropy_normalized"] == 1.0  # max entropy
        assert result["unique_artists"] == 10

    def test_diversity_components(self):
        tracks = [
            _make_track(track_id=f"t{i}", artist=f"A{i % 5}", tempo=100 + i * 10)
            for i in range(10)
        ]
        result = compute_diversity_index(tracks)
        assert 0 <= result["diversity_index"] <= 100
        assert "artist_entropy_normalized" in result
        assert "feature_variance_score" in result
        assert "repeat_ratio" in result


class TestClassifyDimension:
    def test_emotional_tone_ranges(self):
        assert classify_dimension("emotional_tone", 0.1) == "Melancholic"
        assert classify_dimension("emotional_tone", 0.35) == "Reflective"
        assert classify_dimension("emotional_tone", 0.5) == "Balanced"
        assert classify_dimension("emotional_tone", 0.65) == "Positive"
        assert classify_dimension("emotional_tone", 0.9) == "Euphoric"

    def test_energy_level_ranges(self):
        assert classify_dimension("energy_level", 0.2) == "Low Energy"
        assert classify_dimension("energy_level", 0.5) == "Moderate Energy"
        assert classify_dimension("energy_level", 0.6) == "Elevated Energy"
        assert classify_dimension("energy_level", 0.75) == "High Energy"
        assert classify_dimension("energy_level", 0.9) == "Intense Energy"

    def test_tempo_preference_ranges(self):
        assert classify_dimension("tempo_preference", 80) == "Slow"
        assert classify_dimension("tempo_preference", 110) == "Moderate"
        assert classify_dimension("tempo_preference", 120) == "Groovy"
        assert classify_dimension("tempo_preference", 135) == "Upbeat"
        assert classify_dimension("tempo_preference", 150) == "Fast"

    def test_diversity_ranges(self):
        assert classify_dimension("diversity", 20) == "Focused"
        assert classify_dimension("diversity", 40) == "Consistent"
        assert classify_dimension("diversity", 60) == "Balanced"
        assert classify_dimension("diversity", 70) == "Eclectic"
        assert classify_dimension("diversity", 90) == "Wildly Eclectic"

    def test_unknown_dimension(self):
        assert classify_dimension("unknown_dim", 0.5) == "Unknown"


class TestBuildSignature:
    def test_builds_5_dimensions(self):
        aggregated = {
            "valence": {"median": 0.55},
            "energy": {"median": 0.72},
            "acousticness": {"median": 0.35},
            "tempo": {"median": 125.0},
        }
        diversity = {"diversity_index": 68}
        sig = build_signature(aggregated, diversity)
        assert "emotional_tone" in sig
        assert "energy_level" in sig
        assert "musical_complexity" in sig
        assert "tempo_preference" in sig
        assert "diversity" in sig
        assert sig["emotional_tone"]["label"] == "Balanced"
        assert sig["energy_level"]["label"] == "High Energy"


class TestBuildSonicDNA:
    def test_end_to_end(self):
        tracks = [
            _make_track(track_id=f"t{i}", artist=f"A{i % 3}", tempo=100 + i * 5)
            for i in range(20)
        ]
        result = build_sonic_dna(tracks)
        assert result["track_count"] == 20
        assert "audio_features" in result
        assert "diversity" in result
        assert "signature" in result
        assert "top_artists" in result
        assert len(result["top_artists"]) <= 10
