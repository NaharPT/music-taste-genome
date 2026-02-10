"""
Temporal Analyzer - Analyze listening patterns by time of day.

Pure stdlib implementation for Music Taste Genome project.
Windows cp1252 safe - no unicode characters in output.
"""

import statistics
from datetime import datetime
from typing import Optional


def analyze_temporal_patterns(tracks_with_timestamps: list[dict]) -> dict:
    """
    Analyze listening time patterns and feature shifts by time of day.

    Args:
        tracks_with_timestamps: List of track dicts with "played_at" ISO timestamp

    Returns:
        Dictionary with hour distribution, peak hour, morning/evening features,
        and circadian shift metrics
    """
    if not tracks_with_timestamps:
        return {
            "hour_distribution": [0] * 24,
            "peak_hour": None,
            "morning_hours": list(range(6, 12)),
            "evening_hours": list(range(18, 24)),
            "morning_avg_features": None,
            "evening_avg_features": None,
            "circadian_shift": None,
            "total_tracks_with_timestamps": 0
        }

    # Parse timestamps and bin by hour
    hour_distribution = [0] * 24
    morning_tracks = []
    evening_tracks = []

    valid_tracks = 0

    for track in tracks_with_timestamps:
        played_at = track.get("played_at")
        if not played_at:
            continue

        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(played_at.replace("Z", "+00:00"))
            hour = dt.hour

            hour_distribution[hour] += 1
            valid_tracks += 1

            # Categorize by time period
            if 6 <= hour <= 11:
                morning_tracks.append(track)
            elif 18 <= hour <= 23:
                evening_tracks.append(track)

        except (ValueError, AttributeError):
            # Skip invalid timestamps
            continue

    # Find peak hour
    peak_hour = None
    if any(hour_distribution):
        peak_hour = hour_distribution.index(max(hour_distribution))

    # Compute average features for morning and evening
    morning_avg = _compute_period_avg_features(morning_tracks)
    evening_avg = _compute_period_avg_features(evening_tracks)

    # Compute circadian shift
    circadian_shift = None
    if morning_avg and evening_avg:
        circadian_shift = {
            "tempo_delta": round(evening_avg["tempo"] - morning_avg["tempo"], 2),
            "energy_delta": round(evening_avg["energy"] - morning_avg["energy"], 2),
            "valence_delta": round(evening_avg["valence"] - morning_avg["valence"], 2)
        }

    return {
        "hour_distribution": hour_distribution,
        "peak_hour": peak_hour,
        "morning_hours": list(range(6, 12)),
        "evening_hours": list(range(18, 24)),
        "morning_avg_features": morning_avg,
        "evening_avg_features": evening_avg,
        "circadian_shift": circadian_shift,
        "total_tracks_with_timestamps": valid_tracks
    }


def _compute_period_avg_features(tracks: list[dict]) -> Optional[dict]:
    """
    Compute average audio features for a period's tracks.

    Args:
        tracks: List of track dicts

    Returns:
        Dictionary with average tempo, energy, valence, or None if no tracks
    """
    if not tracks:
        return None

    tempo_vals = []
    energy_vals = []
    valence_vals = []

    for track in tracks:
        af = track.get("audio_features", {})
        if not af:
            continue

        if af.get("tempo") is not None:
            tempo_vals.append(af["tempo"])
        if af.get("energy") is not None:
            energy_vals.append(af["energy"])
        if af.get("valence") is not None:
            valence_vals.append(af["valence"])

    if not tempo_vals and not energy_vals and not valence_vals:
        return None

    return {
        "tempo": round(statistics.mean(tempo_vals), 2) if tempo_vals else 0.0,
        "energy": round(statistics.mean(energy_vals), 2) if energy_vals else 0.0,
        "valence": round(statistics.mean(valence_vals), 2) if valence_vals else 0.0
    }


def format_hour_timeline(hour_distribution: list[int], width: int = 30) -> str:
    """
    Generate ASCII 24-hour timeline visualization.

    Args:
        hour_distribution: List of 24 integers (counts per hour)
        width: Maximum bar width in characters

    Returns:
        Multi-line string with timeline visualization
    """
    if not hour_distribution or len(hour_distribution) != 24:
        return ""

    max_count = max(hour_distribution) if hour_distribution else 1
    if max_count == 0:
        max_count = 1

    peak_hour = hour_distribution.index(max(hour_distribution)) if any(hour_distribution) else None

    lines = []
    for hour in range(24):
        count = hour_distribution[hour]

        # Calculate bar length
        bar_length = int((count / max_count) * width) if max_count > 0 else 0
        bar = "=" * bar_length

        # Format hour
        hour_str = f"{hour:02d}:00"

        # Mark peak hour
        peak_marker = "  << peak" if hour == peak_hour and count > 0 else ""

        line = f"{hour_str} |{bar}{peak_marker}"
        lines.append(line)

    return "\n".join(lines)
