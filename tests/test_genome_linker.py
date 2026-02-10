"""Tests for genome linker."""

import json
import pytest
from pathlib import Path
from src.genome_linker import (
    load_genome_findings,
    load_circadian_profile,
    build_genome_context,
    MUSIC_RELEVANT_GENES,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadGenomeFindings:
    def test_load_valid_findings(self):
        result = load_genome_findings(str(FIXTURES / "test_findings.json"))
        assert "CYP1A2" in result
        assert result["CYP1A2"]["status"] == "intermediate"
        assert "COMT" in result
        assert result["COMT"]["status"] == "intermediate"
        assert "BDNF" in result
        assert result["BDNF"]["status"] == "reduced"

    def test_extracts_only_music_relevant(self):
        result = load_genome_findings(str(FIXTURES / "test_findings.json"))
        # APOE is in findings but not music-relevant
        assert "APOE" not in result
        # All returned genes should be in MUSIC_RELEVANT_GENES
        for gene in result:
            assert gene in MUSIC_RELEVANT_GENES

    def test_all_expected_genes(self):
        result = load_genome_findings(str(FIXTURES / "test_findings.json"))
        expected = {"CYP1A2", "COMT", "BDNF", "SLC6A4", "ANKK1", "OPRM1", "ADORA2A"}
        assert set(result.keys()) == expected

    def test_missing_file(self):
        result = load_genome_findings("nonexistent/path/findings.json")
        assert result == {}

    def test_malformed_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        result = load_genome_findings(str(bad_file))
        assert result == {}

    def test_empty_findings(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text('{"findings": []}', encoding="utf-8")
        result = load_genome_findings(str(empty_file))
        assert result == {}

    def test_finding_structure(self):
        result = load_genome_findings(str(FIXTURES / "test_findings.json"))
        cyp = result["CYP1A2"]
        assert "status" in cyp
        assert "gene" in cyp
        assert "description" in cyp
        assert "tier" in cyp
        assert cyp["gene"] == "CYP1A2"


class TestLoadCircadianProfile:
    def test_load_valid_profile(self):
        result = load_circadian_profile(str(FIXTURES / "test_circadian_profile.json"))
        assert result is not None
        assert result["me_score"] == -1
        assert result["me_label"] == "Evening Tendency"
        assert result["rhythm_strength"] == 2

    def test_missing_file(self):
        result = load_circadian_profile("nonexistent/path/profile.json")
        assert result is None

    def test_none_path(self):
        result = load_circadian_profile(None)
        assert result is None

    def test_empty_string_path(self):
        result = load_circadian_profile("")
        assert result is None

    def test_malformed_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        result = load_circadian_profile(str(bad_file))
        assert result is None


class TestBuildGenomeContext:
    def test_full_context(self):
        ctx = build_genome_context(
            str(FIXTURES / "test_findings.json"),
            str(FIXTURES / "test_circadian_profile.json"),
        )
        assert "genes" in ctx
        assert "chronotype" in ctx
        assert "available_correlations" in ctx
        assert ctx["chronotype"] is not None
        assert ctx["chronotype"]["me_score"] == -1

    def test_available_correlations(self):
        ctx = build_genome_context(
            str(FIXTURES / "test_findings.json"),
            str(FIXTURES / "test_circadian_profile.json"),
        )
        available = ctx["available_correlations"]
        assert "caffeine_tempo" in available
        assert "chronotype_hours" in available
        assert "comt_valence" in available
        assert "bdnf_diversity" in available
        assert "serotonin_emotional_range" in available
        assert "drd2_repeat_plays" in available
        assert "oprm1_sad_music" in available

    def test_no_circadian(self):
        ctx = build_genome_context(str(FIXTURES / "test_findings.json"))
        assert ctx["chronotype"] is None
        assert "chronotype_hours" not in ctx["available_correlations"]

    def test_missing_findings(self):
        ctx = build_genome_context("nonexistent.json")
        assert ctx["genes"] == {}
        assert ctx["available_correlations"] == []
