"""Markdown report generator with ASCII visualizations."""

import json
from datetime import datetime
from pathlib import Path


DISCLAIMER = """# Music Taste Genome Report

> **DISCLAIMER**: This is entertainment and self-exploration, NOT science.
> Gene-music correlations are speculative. Your genome influences less than
> half of your behavior. Culture, memory, mood, and pure randomness shape
> your music taste far more than your DNA. Enjoy this as a fun mirror,
> not a diagnostic tool.

---
"""


def ascii_bar(value, max_value=1.0, width=30, label=""):
    """Render a single ASCII bar."""
    if max_value == 0:
        filled = 0
    else:
        filled = int(round((value / max_value) * width))
    filled = max(0, min(width, filled))
    empty = width - filled
    bar = "[" + "#" * filled + "." * empty + "]"
    if label:
        return f"{label:<18} {bar} {value:.2f}"
    return bar


def ascii_bar_int(value, max_value, width=30, label=""):
    """Render an ASCII bar for integer values."""
    if max_value == 0:
        filled = 0
    else:
        filled = int(round((value / max_value) * width))
    filled = max(0, min(width, filled))
    empty = width - filled
    bar = "[" + "#" * filled + "." * empty + "]"
    if label:
        return f"{label:<18} {bar} {value}"
    return bar


def format_audio_profile(features):
    """Format audio features as ASCII bar charts."""
    lines = ["### Audio Feature Profile", ""]

    feature_list = [
        ("Energy", features.get("energy", {}).get("median", 0), 1.0),
        ("Valence", features.get("valence", {}).get("median", 0), 1.0),
        ("Danceability", features.get("danceability", {}).get("median", 0), 1.0),
        ("Acousticness", features.get("acousticness", {}).get("median", 0), 1.0),
        ("Instrumentalness", features.get("instrumentalness", {}).get("median", 0), 1.0),
        ("Speechiness", features.get("speechiness", {}).get("median", 0), 1.0),
        ("Liveness", features.get("liveness", {}).get("median", 0), 1.0),
    ]

    lines.append("```")
    for name, value, max_val in feature_list:
        lines.append(ascii_bar(value, max_val, 30, name))
    lines.append("")

    tempo = features.get("tempo", {})
    if tempo:
        lines.append(
            f"Tempo              {tempo.get('median', 0):.0f} BPM "
            f"(range {tempo.get('min', 0):.0f}-{tempo.get('max', 0):.0f})"
        )

    loudness = features.get("loudness", {})
    if loudness:
        lines.append(
            f"Loudness           {loudness.get('median', 0):.1f} dB "
            f"(range {loudness.get('min', 0):.1f} to {loudness.get('max', 0):.1f})"
        )

    mode_split = features.get("mode_split", {})
    if mode_split:
        major = mode_split.get("major", 0)
        minor = mode_split.get("minor", 0)
        lines.append(f"Mode               {major:.0%} major / {minor:.0%} minor")

    lines.append("```")
    return "\n".join(lines)


def format_key_distribution(features):
    """Format key distribution as mini chart."""
    key_dist = features.get("key_distribution", {})
    if not key_dist:
        return ""

    lines = ["### Key Distribution", "", "```"]
    max_freq = max(key_dist.values()) if key_dist else 1
    for key_name in ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]:
        freq = key_dist.get(key_name, 0)
        bar_len = int(round((freq / max_freq) * 20)) if max_freq > 0 else 0
        lines.append(f"{key_name:<3} {'#' * bar_len:<20} {freq:.1%}")
    lines.append("```")
    return "\n".join(lines)


def format_signature(signature):
    """Format the 5 signature dimensions."""
    lines = ["## Your Sonic DNA Signature", ""]

    dims = [
        ("Emotional Tone", "emotional_tone"),
        ("Energy Level", "energy_level"),
        ("Musical Complexity", "musical_complexity"),
        ("Tempo Preference", "tempo_preference"),
        ("Diversity", "diversity"),
    ]

    for display_name, key in dims:
        dim = signature.get(key, {})
        label = dim.get("label", "Unknown")
        value = dim.get("value", 0)
        if key == "tempo_preference":
            lines.append(f"- **{display_name}**: {label} ({value:.0f} BPM)")
        elif key == "diversity":
            lines.append(f"- **{display_name}**: {label} ({value}/100)")
        else:
            lines.append(f"- **{display_name}**: {label} ({value:.2f})")

    return "\n".join(lines)


def format_temporal(temporal):
    """Format temporal listening patterns."""
    if not temporal:
        return ""

    lines = [
        "## When You Listen",
        "",
        f"Based on {temporal.get('total_tracks_with_timestamps', 0)} recently played tracks:",
        "",
    ]

    hour_dist = temporal.get("hour_distribution", [])
    if hour_dist:
        max_count = max(hour_dist) if hour_dist else 1
        peak = temporal.get("peak_hour", 0)
        lines.append("```")
        for hour in range(24):
            count = hour_dist[hour] if hour < len(hour_dist) else 0
            bar_len = int(round((count / max_count) * 25)) if max_count > 0 else 0
            marker = " << peak" if hour == peak else ""
            lines.append(f"{hour:02d}:00 |{'=' * bar_len}{marker}")
        lines.append("```")

    shift = temporal.get("circadian_shift", {})
    if shift:
        lines.append("")
        lines.append("### Morning vs Evening Shift")
        lines.append("")
        tempo_d = shift.get("tempo_delta")
        energy_d = shift.get("energy_delta")
        valence_d = shift.get("valence_delta")
        if tempo_d is not None:
            sign = "+" if tempo_d >= 0 else ""
            lines.append(f"- Tempo: {sign}{tempo_d:.0f} BPM in the evening")
        if energy_d is not None:
            sign = "+" if energy_d >= 0 else ""
            lines.append(f"- Energy: {sign}{energy_d:.2f} in the evening")
        if valence_d is not None:
            sign = "+" if valence_d >= 0 else ""
            lines.append(f"- Valence: {sign}{valence_d:.2f} in the evening")

    return "\n".join(lines)


def format_correlation(corr, index):
    """Format a single genome x music correlation."""
    lines = [
        f"### {index}. {corr['gene']} x {corr['metric']}",
        "",
        f"**Gene**: {corr['gene']} ({corr['gene_status']})",
        f"**Your Music**: {_format_value(corr['value'])}",
    ]

    expected = corr.get("expected_ranges", {})
    if expected:
        range_lines = []
        for status, rng in expected.items():
            if isinstance(rng, dict):
                mn = rng.get("min", "?")
                mx = rng.get("max", "?")
                range_lines.append(f"{status}: {mn}-{mx}")
            else:
                range_lines.append(f"{status}: {rng}")
        lines.append(f"**Expected Ranges**: {' | '.join(range_lines)}")

    lines.append(f"**Verdict**: {corr['verdict']}")
    lines.append("")

    if corr.get("why_matters"):
        lines.append(f"**Why this might matter**: {corr['why_matters']}")
        lines.append("")

    if corr.get("why_bs"):
        lines.append(f"**Why this might be BS**: {corr['why_bs']}")
        lines.append("")

    lines.append(f"**Confidence**: {corr['confidence'].upper()}")

    return "\n".join(lines)


def _format_value(value):
    """Format a metric value for display."""
    if isinstance(value, float):
        if value > 10:
            return f"{value:.0f}"
        return f"{value:.2f}"
    return str(value)


def format_top_artists(sonic_dna):
    """Format top artists list."""
    top = sonic_dna.get("top_artists", [])
    if not top:
        return ""

    lines = ["### Top Artists (by frequency)", ""]
    for i, artist in enumerate(top[:10], 1):
        if isinstance(artist, dict):
            name = artist.get("name", "Unknown")
            count = artist.get("count", 0)
            lines.append(f"{i:2d}. {name} ({count} tracks)")
        else:
            lines.append(f"{i:2d}. {artist}")
    return "\n".join(lines)


def generate_report(sonic_dna, correlations, temporal=None, output_path="reports/music_taste_genome_report.md"):
    """
    Generate the full Music Taste Genome markdown report.

    Args:
        sonic_dna: Output of build_sonic_dna()
        correlations: Output of correlator.run_all()
        temporal: Output of analyze_temporal_patterns() (optional)
        output_path: Where to write the report
    """
    sections = []

    # Header + disclaimer
    sections.append(DISCLAIMER)

    # Summary stats
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    sections.append(
        f"*Based on {sonic_dna.get('track_count', 0)} tracks "
        f"from {sonic_dna.get('unique_artists', 0)} artists*"
    )
    sections.append("")

    # Sonic DNA signature
    signature = sonic_dna.get("signature", {})
    if signature:
        sections.append(format_signature(signature))
        sections.append("")
        sections.append("---")
        sections.append("")

    # Audio features
    features = sonic_dna.get("audio_features", {})
    if features:
        sections.append("## Audio Deep Dive")
        sections.append("")
        sections.append(format_audio_profile(features))
        sections.append("")
        sections.append(format_key_distribution(features))
        sections.append("")

    # Top artists
    top_artists = format_top_artists(sonic_dna)
    if top_artists:
        sections.append(top_artists)
        sections.append("")

    # Diversity
    diversity = sonic_dna.get("diversity", {})
    if diversity:
        sections.append("### Diversity Metrics")
        sections.append("")
        sections.append(f"- **Diversity Index**: {diversity.get('diversity_index', 0)}/100")
        sections.append(
            f"- **Artist Variety**: {diversity.get('artist_entropy_normalized', 0):.2f} "
            f"(Shannon entropy, normalized)"
        )
        sections.append(
            f"- **Feature Variance**: {diversity.get('feature_variance_score', 0):.2f} "
            f"(how varied your audio features are)"
        )
        sections.append(
            f"- **Repeat Ratio**: {diversity.get('repeat_ratio', 0):.1%} "
            f"(tracks appearing in multiple sources)"
        )
        sections.append("")

    sections.append("---")
    sections.append("")

    # Temporal patterns
    temporal_section = format_temporal(temporal)
    if temporal_section:
        sections.append(temporal_section)
        sections.append("")
        sections.append("---")
        sections.append("")

    # Genome x Music correlations
    if correlations:
        sections.append("## Genome x Music Correlations")
        sections.append("")
        sections.append(
            "> Remember: these are speculative hypotheses based on loose "
            "neuroscience. Your genes are not your destiny, and your Spotify "
            "history is not your genome. This is for fun."
        )
        sections.append("")

        for i, corr in enumerate(correlations, 1):
            sections.append(format_correlation(corr, i))
            sections.append("")
            sections.append("---")
            sections.append("")
    else:
        sections.append("## Genome x Music Correlations")
        sections.append("")
        sections.append(
            "No genome data provided or no relevant genes found. "
            "Run with --genome path/to/findings.json to see correlations."
        )
        sections.append("")

    # Closing
    sections.append("## What to Do With This")
    sections.append("")
    sections.append("1. **Embrace it**: If your genome and music align, lean into it.")
    sections.append("2. **Fight it**: If they don't align, congratulations -- free will wins.")
    sections.append("3. **Share it**: Compare with friends. Who is most genetically predictable?")
    sections.append("4. **Track it**: Re-run in 6 months. See how your sonic DNA shifts.")
    sections.append("5. **Ignore it**: This is entertainment. Just enjoy your music.")
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append("*Generated by Music Taste Genome v1.0*")
    sections.append("*Genome data from genome-insight pipeline*")
    sections.append("*Music data from Spotify API*")

    # Write report
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(sections)
    output.write_text(report_text, encoding="utf-8")
    print(f"Report written to {output_path}")
    return report_text


def export_sonic_dna_json(sonic_dna, correlations=None, temporal=None,
                          output_path="data/profiles/sonic_dna.json"):
    """Export sonic DNA and correlations as JSON for downstream apps."""
    export = {
        "generated_at": datetime.now().isoformat(),
        "pipeline": "Music Taste Genome",
        "sonic_dna": sonic_dna,
        "temporal_patterns": temporal,
        "genome_correlations": correlations or [],
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(export, indent=2, default=str), encoding="utf-8")
    print(f"Sonic DNA JSON exported to {output_path}")
    return export
