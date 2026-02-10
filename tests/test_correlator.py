"""Tests for genome-music correlator."""

import pytest
from src.correlator import GenomeMusicCorrelator


def _make_sonic_dna(
    avg_tempo=125.0,
    avg_valence=0.55,
    valence_std=0.22,
    diversity_index=65,
    repeat_ratio=0.12,
    low_valence_pct=20.0,
):
    return {
        "track_count": 500,
        "unique_artists": 100,
        "audio_features": {
            "tempo": {"mean": avg_tempo, "median": avg_tempo, "std": 15.0},
            "valence": {"mean": avg_valence, "median": avg_valence, "std": valence_std},
            "energy": {"mean": 0.7, "median": 0.7, "std": 0.15},
            "low_valence_pct": low_valence_pct,
        },
        "diversity": {
            "diversity_index": diversity_index,
            "repeat_ratio": repeat_ratio,
        },
        "signature": {},
    }


def _make_genome_context(genes=None, chronotype=None):
    if genes is None:
        genes = {
            "CYP1A2": {"status": "intermediate", "gene": "CYP1A2", "description": "test", "tier": 2},
            "COMT": {"status": "fast", "gene": "COMT", "description": "test", "tier": 2},
            "BDNF": {"status": "normal", "gene": "BDNF", "description": "test", "tier": 2},
            "SLC6A4": {"status": "short", "gene": "SLC6A4", "description": "test", "tier": 2},
            "ANKK1": {"status": "reduced", "gene": "ANKK1", "description": "test", "tier": 2},
            "OPRM1": {"status": "enhanced", "gene": "OPRM1", "description": "test", "tier": 2},
        }
    return {
        "genes": genes,
        "chronotype": chronotype,
        "available_correlations": [],
    }


def _make_temporal(peak_hour=14):
    return {
        "hour_distribution": [0] * 24,
        "peak_hour": peak_hour,
        "morning_avg_features": {"tempo": 118, "energy": 0.65, "valence": 0.50},
        "evening_avg_features": {"tempo": 130, "energy": 0.78, "valence": 0.60},
        "circadian_shift": {"tempo_delta": 12, "energy_delta": 0.13, "valence_delta": 0.10},
        "total_tracks_with_timestamps": 50,
    }


class TestCaffeineTempo:
    def test_returns_result_with_cyp1a2(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(avg_tempo=118),
            _make_genome_context(),
        )
        result = correlator.correlate_caffeine_tempo()
        assert result is not None
        assert result["gene"] == "CYP1A2"
        assert result["id"] == "caffeine_tempo"
        assert result["confidence"] == "weak"

    def test_in_range_verdict(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(avg_tempo=118),
            _make_genome_context(),
        )
        result = correlator.correlate_caffeine_tempo()
        assert "intermediate" in result["verdict"].lower()

    def test_returns_none_without_cyp1a2(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        assert correlator.correlate_caffeine_tempo() is None


class TestChronotypeHours:
    def test_returns_result_with_chronotype(self):
        chronotype = {"me_score": -1, "me_label": "Evening Tendency"}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(chronotype=chronotype),
            _make_temporal(peak_hour=20),
        )
        result = correlator.correlate_chronotype_hours()
        assert result is not None
        assert result["id"] == "chronotype_hours"
        assert result["confidence"] == "moderate"

    def test_returns_none_without_chronotype(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(),
            _make_temporal(),
        )
        assert correlator.correlate_chronotype_hours() is None

    def test_returns_none_without_temporal(self):
        chronotype = {"me_score": 1, "me_label": "Morning Tendency"}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(chronotype=chronotype),
        )
        assert correlator.correlate_chronotype_hours() is None


class TestComtValence:
    def test_returns_result(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(avg_valence=0.65),
            _make_genome_context(),
        )
        result = correlator.correlate_comt_valence()
        assert result is not None
        assert result["gene"] == "COMT"
        assert result["gene_status"] == "fast"
        assert result["value"] == 0.65

    def test_fast_comt_in_range(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(avg_valence=0.65),
            _make_genome_context(),
        )
        result = correlator.correlate_comt_valence()
        assert "confirmed" in result["verdict"].lower() or "economics" in result["verdict"].lower()

    def test_returns_none_without_comt(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        assert correlator.correlate_comt_valence() is None


class TestBdnfDiversity:
    def test_returns_result(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(diversity_index=70),
            _make_genome_context(),
        )
        result = correlator.correlate_bdnf_diversity()
        assert result is not None
        assert result["gene"] == "BDNF"
        assert result["value"] == 70.0

    def test_returns_none_without_bdnf(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        assert correlator.correlate_bdnf_diversity() is None


class TestSerotoninEmotionalRange:
    def test_returns_result(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(valence_std=0.30),
            _make_genome_context(),
        )
        result = correlator.correlate_serotonin_emotional_range()
        assert result is not None
        assert result["gene"] == "SLC6A4"
        assert result["gene_status"] == "short"

    def test_returns_none_without_slc6a4(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        assert correlator.correlate_serotonin_emotional_range() is None


class TestDrd2RepeatPlays:
    def test_returns_result_with_ankk1(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(repeat_ratio=0.25),
            _make_genome_context(),
        )
        result = correlator.correlate_drd2_repeat_plays()
        assert result is not None
        assert result["gene"] == "ANKK1"

    def test_returns_none_without_drd2(self):
        genes = {"CYP1A2": {"status": "fast", "gene": "CYP1A2", "description": "", "tier": 2}}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes=genes),
        )
        assert correlator.correlate_drd2_repeat_plays() is None


class TestOprm1SadMusic:
    def test_returns_result(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(low_valence_pct=30.0),
            _make_genome_context(),
        )
        result = correlator.correlate_oprm1_sad_music()
        assert result is not None
        assert result["gene"] == "OPRM1"
        assert result["gene_status"] == "enhanced"
        assert result["value"] == 30.0

    def test_returns_none_without_oprm1(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        assert correlator.correlate_oprm1_sad_music() is None


class TestRunAll:
    def test_runs_all_available(self):
        chronotype = {"me_score": -1, "me_label": "Evening Tendency"}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(low_valence_pct=25.0),
            _make_genome_context(chronotype=chronotype),
            _make_temporal(peak_hour=20),
        )
        results = correlator.run_all()
        # Should have all 7 correlations
        assert len(results) == 7

    def test_sorted_by_confidence(self):
        chronotype = {"me_score": -1, "me_label": "Evening Tendency"}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(low_valence_pct=25.0),
            _make_genome_context(chronotype=chronotype),
            _make_temporal(),
        )
        results = correlator.run_all()
        confidence_order = {"moderate": 0, "weak": 1, "speculative": 2}
        for i in range(len(results) - 1):
            current = confidence_order.get(results[i]["confidence"], 3)
            next_val = confidence_order.get(results[i + 1]["confidence"], 3)
            assert current <= next_val

    def test_skips_missing_genes(self):
        genes = {"CYP1A2": {"status": "fast", "gene": "CYP1A2", "description": "", "tier": 2}}
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes=genes),
        )
        results = correlator.run_all()
        assert len(results) == 1  # only caffeine_tempo
        assert results[0]["id"] == "caffeine_tempo"

    def test_empty_genome(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(genes={}),
        )
        results = correlator.run_all()
        assert results == []

    def test_result_structure(self):
        correlator = GenomeMusicCorrelator(
            _make_sonic_dna(),
            _make_genome_context(),
        )
        results = correlator.run_all()
        for result in results:
            assert "id" in result
            assert "gene" in result
            assert "gene_status" in result
            assert "metric" in result
            assert "value" in result
            assert "verdict" in result
            assert "why_matters" in result
            assert "why_bs" in result
            assert "confidence" in result
