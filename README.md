# Music Taste Genome

Python analyzers for Spotify listening data. Pure stdlib implementation (no external dependencies).

## Modules

### 1. `src/analyzers/sonic_profiler.py`

Aggregates Spotify audio features into a sonic DNA personality profile.

**Key functions:**
- `aggregate_audio_features(tracks)` - Compute statistics (mean/median/std/percentiles) for audio features
- `compute_diversity_index(tracks)` - Calculate musical diversity (0-100 scale) using artist entropy, feature variance, and repeat ratio
- `build_signature(aggregated, diversity)` - Generate 5 signature dimensions with human-readable labels
- `build_sonic_dna(tracks)` - Master function: complete profile with all metrics

**Signature dimensions:**
- **Emotional Tone** (from valence): Melancholic → Reflective → Balanced → Positive → Euphoric
- **Energy Level** (from energy): Low → Moderate → Elevated → High → Intense
- **Musical Complexity** (from acousticness): Digital/Electronic → Mix → Acoustic/Organic
- **Tempo Preference** (from tempo): Slow → Moderate → Groovy → Upbeat → Fast
- **Diversity** (from diversity index): Focused → Consistent → Balanced → Eclectic → Wildly Eclectic

### 2. `src/analyzers/temporal_analyzer.py`

Analyzes listening patterns by time of day and circadian feature shifts.

**Key functions:**
- `analyze_temporal_patterns(tracks_with_timestamps)` - Analyze hour distribution, morning/evening features, circadian shifts
- `format_hour_timeline(hour_distribution, width=30)` - ASCII visualization of 24-hour listening pattern

**Circadian metrics:**
- Morning period: 6:00-11:00
- Evening period: 18:00-23:00
- Delta calculation: evening avg - morning avg for tempo, energy, valence

## Usage

```python
from src.analyzers import sonic_profiler, temporal_analyzer

# Sonic profiling
tracks = [
    {
        "id": "track_id",
        "name": "Song Name",
        "artists": ["Artist"],
        "audio_features": {
            "tempo": 125.3,
            "energy": 0.72,
            "valence": 0.58,
            # ... other features
        }
    }
]

dna = sonic_profiler.build_sonic_dna(tracks)
print(f"Diversity: {dna['diversity']['diversity_index']}/100")
print(f"Signature: {dna['signature']}")

# Temporal analysis
timestamped_tracks = [
    {
        "played_at": "2026-02-10T14:30:00Z",
        "audio_features": {...}
    }
]

patterns = temporal_analyzer.analyze_temporal_patterns(timestamped_tracks)
print(f"Peak hour: {patterns['peak_hour']}:00")
print(temporal_analyzer.format_hour_timeline(patterns['hour_distribution']))
```

## Testing

Run the included test script:

```bash
python test_analyzers.py
```

## Requirements

- Python 3.11+
- No external dependencies (pure stdlib)
- Windows cp1252 encoding safe (no unicode in output)

## Implementation Notes

- All numeric outputs rounded to 2 decimal places
- Shannon entropy used for artist diversity
- Coefficient of variation used for feature variance
- Percentiles computed by sorted list indexing (25th/75th)
- ISO 8601 timestamp parsing for temporal analysis
