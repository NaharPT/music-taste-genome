"""
Sonic DNA Profiler - Aggregate Spotify audio features into personality profiles.

Pure stdlib implementation for Music Taste Genome project.
Windows cp1252 safe - no unicode characters in output.
"""

import math
import statistics
from collections import Counter
from typing import Any


KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def aggregate_audio_features(tracks: list[dict]) -> dict:
    """
    Compute statistics for each audio feature.

    Args:
        tracks: List of track dicts with audio_features sub-dict

    Returns:
        Dictionary with mean/median/std/percentiles for each feature,
        plus key distribution, mode split, and average duration.
    """
    if not tracks:
        return {}

    # Collect feature values
    features = {
        "tempo": [],
        "energy": [],
        "valence": [],
        "danceability": [],
        "acousticness": [],
        "instrumentalness": [],
        "loudness": [],
        "speechiness": [],
        "liveness": []
    }

    keys = []
    modes = []
    durations = []

    for track in tracks:
        af = track.get("audio_features", {})
        if not af:
            continue

        for feature_name in features.keys():
            val = af.get(feature_name)
            if val is not None:
                features[feature_name].append(val)

        if af.get("key") is not None:
            keys.append(af["key"])
        if af.get("mode") is not None:
            modes.append(af["mode"])
        if af.get("duration_ms") is not None:
            durations.append(af["duration_ms"])

    # Compute stats for each feature
    result = {}

    for feature_name, values in features.items():
        if not values:
            continue

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        result[feature_name] = {
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "std": round(statistics.stdev(values), 2) if n > 1 else 0.0,
            "p25": round(sorted_vals[n // 4], 2),
            "p75": round(sorted_vals[3 * n // 4], 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2)
        }

    # Key distribution
    if keys:
        key_counts = Counter(keys)
        total_keys = len(keys)
        result["key_distribution"] = {
            KEY_NAMES[k]: round(count / total_keys, 2)
            for k, count in sorted(key_counts.items())
        }
    else:
        result["key_distribution"] = {}

    # Mode split (major/minor)
    if modes:
        mode_counts = Counter(modes)
        total_modes = len(modes)
        result["mode_split"] = {
            "major": round(mode_counts.get(1, 0) / total_modes, 2),
            "minor": round(mode_counts.get(0, 0) / total_modes, 2)
        }
    else:
        result["mode_split"] = {"major": 0.0, "minor": 0.0}

    # Average duration in seconds
    if durations:
        result["avg_duration_sec"] = round(statistics.mean(durations) / 1000, 0)
    else:
        result["avg_duration_sec"] = 0

    # Low-valence percentage (tracks with valence < 0.35)
    valence_values = features.get("valence", [])
    if valence_values:
        low_valence_count = sum(1 for v in valence_values if v < 0.35)
        result["low_valence_pct"] = round((low_valence_count / len(valence_values)) * 100, 1)
    else:
        result["low_valence_pct"] = 0.0

    return result


def compute_diversity_index(tracks: list[dict]) -> dict:
    """
    Calculate musical diversity metrics on 0-100 scale.

    Components:
    - artist_entropy: Shannon entropy normalized by log(unique_artists)
    - feature_variance: average coefficient of variation across key features
    - repeat_ratio: proportion of repeated tracks (inverted for diversity)

    diversity_index = weighted average * 100

    Args:
        tracks: List of track dicts

    Returns:
        Dictionary with diversity_index (0-100) and component scores
    """
    if not tracks:
        return {
            "diversity_index": 0,
            "artist_entropy_normalized": 0.0,
            "feature_variance_score": 0.0,
            "repeat_ratio": 0.0,
            "unique_artists": 0,
            "unique_tracks": 0,
            "total_tracks": 0
        }

    # Artist entropy
    artists = []
    for track in tracks:
        track_artists = track.get("artists", [])
        if track_artists:
            # Use first artist
            artists.append(track_artists[0] if isinstance(track_artists, list) else track_artists)

    unique_artists = len(set(artists)) if artists else 0
    artist_counts = Counter(artists)
    total_artists = len(artists)

    if unique_artists > 1 and total_artists > 0:
        # Shannon entropy: -sum(p * log(p))
        entropy = 0.0
        for count in artist_counts.values():
            p = count / total_artists
            if p > 0:
                entropy -= p * math.log(p)

        # Normalize by max possible entropy (log of unique artists)
        max_entropy = math.log(unique_artists)
        artist_entropy_normalized = entropy / max_entropy if max_entropy > 0 else 0.0
    else:
        artist_entropy_normalized = 0.0

    # Feature variance score (coefficient of variation)
    feature_names = ["tempo", "energy", "valence", "danceability"]
    cv_scores = []

    for feature_name in feature_names:
        values = []
        for track in tracks:
            af = track.get("audio_features", {})
            val = af.get(feature_name)
            if val is not None:
                values.append(val)

        if len(values) > 1:
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values)
            if mean_val > 0:
                cv = std_val / mean_val
                # Cap CV at 1.0 for scoring purposes
                cv_scores.append(min(cv, 1.0))

    feature_variance_score = statistics.mean(cv_scores) if cv_scores else 0.0

    # Repeat ratio
    track_ids = [t.get("id") for t in tracks if t.get("id")]
    unique_tracks = len(set(track_ids)) if track_ids else 0
    total_tracks = len(track_ids) if track_ids else len(tracks)
    repeat_ratio = 1 - (unique_tracks / total_tracks) if total_tracks > 0 else 0.0

    # Weighted diversity index
    diversity_score = (
        0.4 * artist_entropy_normalized +
        0.4 * feature_variance_score +
        0.2 * (1 - repeat_ratio)
    )
    diversity_index = round(diversity_score * 100)

    return {
        "diversity_index": diversity_index,
        "artist_entropy_normalized": round(artist_entropy_normalized, 2),
        "feature_variance_score": round(feature_variance_score, 2),
        "repeat_ratio": round(repeat_ratio, 2),
        "unique_artists": unique_artists,
        "unique_tracks": unique_tracks,
        "total_tracks": total_tracks
    }


def classify_dimension(name: str, value: float) -> str:
    """
    Classify a numeric value into human-readable label.

    Args:
        name: Dimension name (emotional_tone, energy_level, etc.)
        value: Numeric value to classify

    Returns:
        Human-readable label string
    """
    if name == "emotional_tone":
        if value < 0.3:
            return "Melancholic"
        elif value < 0.45:
            return "Reflective"
        elif value < 0.6:
            return "Balanced"
        elif value < 0.75:
            return "Positive"
        else:
            return "Euphoric"

    elif name == "energy_level":
        if value < 0.35:
            return "Low Energy"
        elif value < 0.55:
            return "Moderate Energy"
        elif value < 0.7:
            return "Elevated Energy"
        elif value < 0.85:
            return "High Energy"
        else:
            return "Intense Energy"

    elif name == "musical_complexity":
        if value < 0.2:
            return "Digital/Electronic"
        elif value < 0.4:
            return "Electronic-Leaning"
        elif value < 0.6:
            return "Electronic-Acoustic Mix"
        elif value < 0.8:
            return "Acoustic-Leaning"
        else:
            return "Acoustic/Organic"

    elif name == "tempo_preference":
        if value < 100:
            return "Slow"
        elif value < 115:
            return "Moderate"
        elif value < 128:
            return "Groovy"
        elif value < 140:
            return "Upbeat"
        else:
            return "Fast"

    elif name == "diversity":
        if value < 30:
            return "Focused"
        elif value < 50:
            return "Consistent"
        elif value < 65:
            return "Balanced"
        elif value < 80:
            return "Eclectic"
        else:
            return "Wildly Eclectic"

    return "Unknown"


def build_signature(aggregated: dict, diversity: dict) -> dict:
    """
    Build 5 signature dimensions from aggregated features.

    Args:
        aggregated: Output from aggregate_audio_features()
        diversity: Output from compute_diversity_index()

    Returns:
        Dictionary with 5 signature dimensions, each with value and label
    """
    signature = {}

    # Emotional tone (from valence)
    if "valence" in aggregated:
        valence_median = aggregated["valence"]["median"]
        signature["emotional_tone"] = {
            "value": valence_median,
            "label": classify_dimension("emotional_tone", valence_median)
        }

    # Energy level
    if "energy" in aggregated:
        energy_median = aggregated["energy"]["median"]
        signature["energy_level"] = {
            "value": energy_median,
            "label": classify_dimension("energy_level", energy_median)
        }

    # Musical complexity (from acousticness)
    if "acousticness" in aggregated:
        acousticness_median = aggregated["acousticness"]["median"]
        signature["musical_complexity"] = {
            "value": acousticness_median,
            "label": classify_dimension("musical_complexity", acousticness_median)
        }

    # Tempo preference
    if "tempo" in aggregated:
        tempo_median = aggregated["tempo"]["median"]
        signature["tempo_preference"] = {
            "value": tempo_median,
            "label": classify_dimension("tempo_preference", tempo_median)
        }

    # Diversity
    diversity_index = diversity.get("diversity_index", 0)
    signature["diversity"] = {
        "value": diversity_index,
        "label": classify_dimension("diversity", diversity_index)
    }

    return signature


def build_sonic_dna(tracks: list[dict]) -> dict:
    """
    Master function: generate complete sonic DNA profile.

    Args:
        tracks: List of track dicts with audio_features

    Returns:
        Complete profile with aggregated features, diversity metrics,
        signature dimensions, and top artists
    """
    # Aggregate features
    aggregated = aggregate_audio_features(tracks)

    # Compute diversity
    diversity = compute_diversity_index(tracks)

    # Build signature
    signature = build_signature(aggregated, diversity)

    # Top artists
    artists = []
    for track in tracks:
        track_artists = track.get("artists", [])
        if track_artists:
            artist = track_artists[0] if isinstance(track_artists, list) else track_artists
            artists.append(artist)

    artist_counts = Counter(artists)
    top_artists = [artist for artist, count in artist_counts.most_common(10)]

    # Assemble full profile
    profile = {
        "track_count": len(tracks),
        "unique_artists": diversity["unique_artists"],
        "audio_features": aggregated,
        "diversity": diversity,
        "signature": signature,
        "top_artists": top_artists
    }

    return profile
