"""
Genome Linker - Extract music-relevant genomic findings.

Reads findings.json and circadian_profile.json from genome-insight project
and extracts gene statuses relevant to music taste correlations.
"""

import json
from pathlib import Path

# Genes relevant to music taste correlations
MUSIC_RELEVANT_GENES = {
    "CYP1A2": "caffeine_metabolism",
    "COMT": "dopamine_metabolism",
    "BDNF": "neuroplasticity",
    "SLC6A4": "serotonin_transport",
    "ANKK1": "dopamine_receptor",
    "DRD2": "dopamine_receptor",   # alias for ANKK1/DRD2
    "OPRM1": "opioid_receptor",
    "ADORA2A": "adenosine_receptor",
}


def load_genome_findings(findings_path: str) -> dict:
    """
    Load findings.json and extract music-relevant gene statuses.

    Returns: {
        "CYP1A2": {"status": "intermediate", "gene": "CYP1A2", "description": "...", "tier": 2},
        "COMT": {"status": "fast", ...},
        ... (only genes found in findings)
    }

    Gracefully handles: missing file, malformed JSON, missing genes.
    Missing genes get status="unknown".
    """
    path = Path(findings_path)

    if not path.exists():
        print(f"Warning: findings.json not found at {findings_path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load findings.json: {e}")
        return {}

    findings = data.get("findings", [])
    if not findings:
        print("Warning: No findings in findings.json")
        return {}

    # Extract music-relevant genes
    gene_data = {}

    for finding in findings:
        gene = finding.get("gene")
        if not gene or gene not in MUSIC_RELEVANT_GENES:
            continue

        # Skip if we already have this gene (take first occurrence)
        if gene in gene_data:
            continue

        status = finding.get("status", "unknown")
        description = finding.get("description", "")
        title = finding.get("title", "")
        tier = finding.get("tier", 0)

        gene_data[gene] = {
            "status": status,
            "gene": gene,
            "description": description,
            "title": title,
            "tier": tier,
        }

    return gene_data


def load_circadian_profile(profile_path: str) -> dict | None:
    """
    Load circadian_profile.json if it exists.

    Returns: {
        "me_score": -1,
        "me_label": "Evening Tendency",
        "rhythm_strength": 2,
        "rhythm_label": "Robust",
        "caffeine_sensitivity": 1,
        "caffeine_sensitivity_label": "Normal"
    }

    Returns None if file doesn't exist or is malformed.
    """
    if not profile_path:
        return None

    path = Path(profile_path)

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load circadian_profile.json: {e}")
        return None

    chronotype = data.get("chronotype_profile")
    if not chronotype:
        return None

    return {
        "me_score": chronotype.get("me_score", 0),
        "me_label": chronotype.get("me_label", "Unknown"),
        "rhythm_strength": chronotype.get("rhythm_strength", 0),
        "rhythm_label": chronotype.get("rhythm_label", "Unknown"),
        "caffeine_sensitivity": chronotype.get("caffeine_sensitivity", 0),
        "caffeine_sensitivity_label": chronotype.get("caffeine_sensitivity_label", "Unknown"),
    }


def build_genome_context(findings_path: str, circadian_path: str = None) -> dict:
    """
    Build complete genome context for correlation engine.

    Returns: {
        "genes": {gene: {status, description, tier}},
        "chronotype": {me_score, me_label, ...} or None,
        "available_correlations": ["caffeine_tempo", "chronotype_hours", ...]
    }
    """
    genes = load_genome_findings(findings_path)
    chronotype = load_circadian_profile(circadian_path) if circadian_path else None

    # Determine which correlations are possible based on available genes
    available = []

    if "CYP1A2" in genes:
        available.append("caffeine_tempo")

    if chronotype is not None:
        available.append("chronotype_hours")

    if "COMT" in genes:
        available.append("comt_valence")

    if "BDNF" in genes:
        available.append("bdnf_diversity")

    if "SLC6A4" in genes:
        available.append("serotonin_emotional_range")

    if "DRD2" in genes or "ANKK1" in genes:
        available.append("drd2_repeat_plays")

    if "OPRM1" in genes:
        available.append("oprm1_sad_music")

    return {
        "genes": genes,
        "chronotype": chronotype,
        "available_correlations": available,
    }
