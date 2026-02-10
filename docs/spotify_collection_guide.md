# Spotify Data Collection Guide

## Overview

Two Python modules for collecting listening history and audio features from Spotify:

1. **`src/auth/spotify_auth.py`** - OAuth2 PKCE authentication flow
2. **`src/collectors/spotify_collector.py`** - API data collection with rate limiting

## Setup

### 1. Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app (or use existing)
3. Copy the Client ID
4. Add redirect URI: `http://localhost:8888/callback`

### 2. Configure Environment

```bash
# Copy .env.example to .env
copy .env.example .env

# Edit .env and add your credentials
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

## Quick Start

### Command Line Collection

```bash
python scripts\collect_spotify_data.py
```

This will:
1. Open browser for Spotify authorization (first run only)
2. Collect recently played, top tracks, and saved library
3. Fetch audio features for all tracks
4. Save to `data/cache/spotify_collection.json`

### Programmatic Usage

```python
from auth.spotify_auth import SpotifyAuthenticator
from collectors.spotify_collector import SpotifyCollector

# Initialize
auth = SpotifyAuthenticator(client_id="your_client_id")
collector = SpotifyCollector(auth=auth)

# Collect full profile
profile = collector.collect_full_profile()

# Or collect specific data
recently_played = collector.get_recently_played(limit=50)
top_tracks = collector.get_top_tracks(time_range="medium_term", limit=50)
saved_tracks = collector.get_saved_tracks(limit=500)

# Get audio features for specific tracks
track_ids = [track["track_id"] for track in recently_played]
features = collector.get_audio_features(track_ids)
```

## Authentication Flow

### First Run

1. Script opens browser to Spotify authorization page
2. User grants permissions (read recently played, top tracks, saved library)
3. Spotify redirects to local callback server
4. Script exchanges code for access + refresh tokens
5. Tokens cached to `data/cache/.spotify_token.json`

### Subsequent Runs

- Tokens loaded from cache
- Auto-refreshed if expired
- Full re-auth only if refresh token invalid

## Data Collected

### Track Metadata

- `track_id` - Spotify track ID
- `name` - Track name
- `artists` - List of artist names
- `album_name` - Album name
- `duration_ms` - Track duration
- `source` - Collection source (recently_played, top_short, top_medium, top_long, saved_library)
- `played_at` - Timestamp (recently played only)
- `added_at` - Timestamp (saved library only)

### Audio Features

- `tempo` - BPM
- `key` - Musical key (0-11)
- `mode` - Major (1) or minor (0)
- `energy` - 0.0 to 1.0
- `valence` - Musical positivity (0.0 to 1.0)
- `danceability` - 0.0 to 1.0
- `acousticness` - 0.0 to 1.0
- `instrumentalness` - 0.0 to 1.0
- `loudness` - dB
- `speechiness` - 0.0 to 1.0
- `liveness` - 0.0 to 1.0
- `time_signature` - Beats per bar

### Collection Sources

- **Recently Played**: Last 50 tracks played
- **Top Tracks (Short)**: Top 50 from last 4 weeks
- **Top Tracks (Medium)**: Top 50 from last 6 months
- **Top Tracks (Long)**: Top 50 from last several years
- **Saved Library**: Up to 500 saved tracks

Total possible: ~700 tracks (deduplicated to unique IDs)

## Rate Limiting

The collector implements:
- 1 second minimum delay between requests
- Automatic retry with exponential backoff on 429 responses
- Respects Spotify's `Retry-After` header
- Maximum 3 retries per request

## Error Handling

- **Token expired**: Auto-refresh using refresh token
- **Refresh token invalid**: Prompts full re-authentication
- **Rate limit (429)**: Exponential backoff with retries
- **Missing audio features**: Gracefully skipped (some tracks lack features)
- **API errors**: Logged and collection continues for remaining sources

## Output Format

`data/cache/spotify_collection.json`:

```json
{
  "collected_at": "2026-02-10T14:30:00",
  "sources": {
    "recently_played": 50,
    "top_short": 50,
    "top_medium": 50,
    "top_long": 50,
    "saved_library": 450
  },
  "tracks": [
    {
      "track_id": "spotify:track:...",
      "name": "Track Name",
      "artists": ["Artist 1", "Artist 2"],
      "album_name": "Album",
      "duration_ms": 240000,
      "source": "top_medium",
      "tempo": 120.5,
      "energy": 0.85,
      "valence": 0.72,
      ...
    }
  ],
  "unique_artists": ["Artist 1", "Artist 2", ...],
  "total_unique_tracks": 650,
  "total_unique_artists": 230,
  "tracks_with_features": 645
}
```

## Security Notes

- Tokens stored locally in `data/cache/.spotify_token.json` (gitignored)
- Uses OAuth2 PKCE flow (no client secret required)
- Token refresh automatic and transparent
- No user credentials stored

## Troubleshooting

### Browser doesn't open automatically

Copy the auth URL from console and paste into browser manually.

### "Invalid redirect URI" error

Verify `http://localhost:8888/callback` is added to your Spotify app's redirect URIs in the dashboard.

### Port 8888 already in use

Change `SPOTIFY_REDIRECT_URI` in `.env` to use different port (e.g., `http://localhost:8889/callback`).

### Rate limiting issues

Collection script respects Spotify rate limits. If issues persist, increase `_rate_limit_delay` in `SpotifyCollector.__init__()`.

### Missing audio features

Some tracks (especially newer releases) may not have audio features. This is normal and handled gracefully.
