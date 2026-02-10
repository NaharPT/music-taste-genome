"""Collect listening data and audio features from Spotify API."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests


class SpotifyCollector:
    """Collect listening data and audio features from Spotify API."""

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, auth):
        """
        Initialize Spotify collector.

        Args:
            auth: SpotifyAuthenticator instance for token management
        """
        self.auth = auth
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._rate_limit_delay = 1.0  # seconds between requests
        self._last_request_time = 0.0

    def _request(self, endpoint: str, params: dict = None) -> dict:
        """
        Make authenticated GET request with rate limiting and retry on 429.

        Args:
            endpoint: API endpoint path (e.g., "/me/player/recently-played")
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            requests.HTTPError: If request fails after retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        max_retries = 3
        retry_count = 0

        while retry_count <= max_retries:
            # Rate limiting: ensure minimum delay between requests
            elapsed = time.time() - self._last_request_time
            if elapsed < self._rate_limit_delay:
                time.sleep(self._rate_limit_delay - elapsed)

            # Get valid token (auto-refresh if needed)
            token = self.auth.get_valid_token()
            headers = {"Authorization": f"Bearer {token}"}

            self._last_request_time = time.time()
            response = requests.get(url, headers=headers, params=params)

            # Handle rate limiting
            if response.status_code == 429:
                retry_count += 1
                if retry_count > max_retries:
                    response.raise_for_status()

                # Exponential backoff with Retry-After header
                retry_after = int(response.headers.get("Retry-After", 1))
                wait_time = retry_after * (2 ** (retry_count - 1))
                print(f"Rate limited. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}...")
                time.sleep(wait_time)
                continue

            # Raise for other errors
            response.raise_for_status()
            return response.json()

        # Should not reach here
        raise RuntimeError("Max retries exceeded")

    def get_recently_played(self, limit: int = 50) -> list[dict]:
        """
        Fetch recently played tracks (max 50).

        Args:
            limit: Number of tracks to fetch (max 50)

        Returns:
            List of track dictionaries with metadata
        """
        print("Fetching recently played tracks...")
        params = {"limit": min(limit, 50)}
        data = self._request("/me/player/recently-played", params)

        tracks = []
        for item in data.get("items", []):
            track = item["track"]
            tracks.append({
                "track_id": track["id"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "album_name": track["album"]["name"],
                "duration_ms": track["duration_ms"],
                "played_at": item["played_at"],
                "source": "recently_played"
            })

        print(f"Fetched {len(tracks)} recently played tracks")
        return tracks

    def get_top_tracks(self, time_range: str = "medium_term", limit: int = 50) -> list[dict]:
        """
        Fetch top tracks for a given time range.

        Args:
            time_range: One of "short_term" (4 weeks), "medium_term" (6 months),
                       "long_term" (several years)
            limit: Number of tracks to fetch (max 50)

        Returns:
            List of track dictionaries with metadata
        """
        print(f"Fetching top tracks ({time_range})...")
        params = {
            "time_range": time_range,
            "limit": min(limit, 50)
        }
        data = self._request("/me/top/tracks", params)

        tracks = []
        for track in data.get("items", []):
            tracks.append({
                "track_id": track["id"],
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "album_name": track["album"]["name"],
                "duration_ms": track["duration_ms"],
                "source": f"top_{time_range}"
            })

        print(f"Fetched {len(tracks)} top tracks ({time_range})")
        return tracks

    def get_saved_tracks(self, limit: int = 500) -> list[dict]:
        """
        Fetch saved library tracks with pagination.

        Args:
            limit: Maximum number of tracks to fetch

        Returns:
            List of track dictionaries with metadata
        """
        print("Fetching saved library tracks...")
        tracks = []
        offset = 0
        page_size = 20  # Spotify API page size for saved tracks

        while len(tracks) < limit:
            params = {
                "limit": page_size,
                "offset": offset
            }
            data = self._request("/me/tracks", params)

            items = data.get("items", [])
            if not items:
                break  # No more tracks

            for item in items:
                track = item["track"]
                tracks.append({
                    "track_id": track["id"],
                    "name": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "album_name": track["album"]["name"],
                    "duration_ms": track["duration_ms"],
                    "added_at": item["added_at"],
                    "source": "saved_library"
                })

                if len(tracks) >= limit:
                    break

            offset += page_size

            # Check if we've fetched all available tracks
            if offset >= data.get("total", 0):
                break

        print(f"Fetched {len(tracks)} saved library tracks")
        return tracks

    def get_audio_features(self, track_ids: list[str]) -> dict:
        """
        Batch fetch audio features for multiple tracks.

        Args:
            track_ids: List of Spotify track IDs (up to 100 per request)

        Returns:
            Dictionary mapping track_id to audio features dict
        """
        if not track_ids:
            return {}

        print(f"Fetching audio features for {len(track_ids)} tracks...")
        features_map = {}
        batch_size = 100

        # Process in batches of 100
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i + batch_size]
            params = {"ids": ",".join(batch)}

            data = self._request("/audio-features", params)

            for features in data.get("audio_features", []):
                if features is None:
                    # Some tracks may not have audio features
                    continue

                track_id = features["id"]
                features_map[track_id] = {
                    "tempo": features.get("tempo"),
                    "key": features.get("key"),
                    "mode": features.get("mode"),
                    "energy": features.get("energy"),
                    "valence": features.get("valence"),
                    "danceability": features.get("danceability"),
                    "acousticness": features.get("acousticness"),
                    "instrumentalness": features.get("instrumentalness"),
                    "loudness": features.get("loudness"),
                    "speechiness": features.get("speechiness"),
                    "liveness": features.get("liveness"),
                    "time_signature": features.get("time_signature")
                }

            if len(track_ids) > batch_size:
                print(f"Progress: {min(i + batch_size, len(track_ids))}/{len(track_ids)} tracks processed")

        print(f"Retrieved audio features for {len(features_map)} tracks")
        return features_map

    def collect_full_profile(self) -> dict:
        """
        End-to-end collection of listening profile with audio features.

        This method:
        1. Fetches recently played tracks (50)
        2. Fetches top tracks for short/medium/long term (50 each)
        3. Fetches saved library tracks (up to 500)
        4. Deduplicates by track_id
        5. Batch fetches audio features for all unique tracks
        6. Saves to data/cache/spotify_collection.json

        Returns:
            Complete profile dictionary with tracks and metadata
        """
        print("=" * 60)
        print("Starting full Spotify profile collection...")
        print("=" * 60)

        collected_tracks = []
        sources_count = {}

        # 1. Recently played
        try:
            recently_played = self.get_recently_played(limit=50)
            collected_tracks.extend(recently_played)
            sources_count["recently_played"] = len(recently_played)
        except Exception as e:
            print(f"Error fetching recently played: {e}")
            sources_count["recently_played"] = 0

        # 2. Top tracks - short term (4 weeks)
        try:
            top_short = self.get_top_tracks(time_range="short_term", limit=50)
            collected_tracks.extend(top_short)
            sources_count["top_short"] = len(top_short)
        except Exception as e:
            print(f"Error fetching top short term: {e}")
            sources_count["top_short"] = 0

        # 3. Top tracks - medium term (6 months)
        try:
            top_medium = self.get_top_tracks(time_range="medium_term", limit=50)
            collected_tracks.extend(top_medium)
            sources_count["top_medium"] = len(top_medium)
        except Exception as e:
            print(f"Error fetching top medium term: {e}")
            sources_count["top_medium"] = 0

        # 4. Top tracks - long term (years)
        try:
            top_long = self.get_top_tracks(time_range="long_term", limit=50)
            collected_tracks.extend(top_long)
            sources_count["top_long"] = len(top_long)
        except Exception as e:
            print(f"Error fetching top long term: {e}")
            sources_count["top_long"] = 0

        # 5. Saved library
        try:
            saved = self.get_saved_tracks(limit=500)
            collected_tracks.extend(saved)
            sources_count["saved_library"] = len(saved)
        except Exception as e:
            print(f"Error fetching saved library: {e}")
            sources_count["saved_library"] = 0

        print("\n" + "=" * 60)
        print("Deduplicating tracks...")

        # Deduplicate by track_id, keeping first occurrence
        seen_ids = set()
        unique_tracks = []
        for track in collected_tracks:
            if track["track_id"] not in seen_ids:
                seen_ids.add(track["track_id"])
                unique_tracks.append(track)

        print(f"Total tracks collected: {len(collected_tracks)}")
        print(f"Unique tracks: {len(unique_tracks)}")

        # 6. Fetch audio features
        print("\n" + "=" * 60)
        track_ids = [track["track_id"] for track in unique_tracks]
        audio_features = self.get_audio_features(track_ids)

        # Merge audio features into tracks (nested under "audio_features" key)
        for track in unique_tracks:
            features = audio_features.get(track["track_id"])
            if features:
                track["audio_features"] = features
            else:
                track["audio_features"] = None

        # Extract unique artists
        unique_artists = set()
        for track in unique_tracks:
            unique_artists.update(track["artists"])

        # Build final profile
        profile = {
            "collected_at": datetime.now().isoformat(),
            "sources": sources_count,
            "tracks": unique_tracks,
            "unique_artists": sorted(unique_artists),
            "total_unique_tracks": len(unique_tracks),
            "total_unique_artists": len(unique_artists),
            "tracks_with_features": len(audio_features)
        }

        # Save to cache
        output_file = "spotify_collection.json"
        self._save_cache(profile, output_file)

        print("\n" + "=" * 60)
        print("Collection complete!")
        print(f"Total unique tracks: {profile['total_unique_tracks']}")
        print(f"Total unique artists: {profile['total_unique_artists']}")
        print(f"Tracks with audio features: {profile['tracks_with_features']}")
        print(f"Saved to: {self.cache_dir / output_file}")
        print("=" * 60)

        return profile

    def _save_cache(self, data: dict, filename: str):
        """
        Save data to cache directory as JSON.

        Args:
            data: Dictionary to save
            filename: Output filename
        """
        output_path = self.cache_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_cache(self, filename: str, max_age_days: int = 7) -> Optional[dict]:
        """
        Load data from cache if exists and not expired.

        Args:
            filename: Cache filename
            max_age_days: Maximum age in days for cache to be valid

        Returns:
            Cached data dictionary or None if not found/expired
        """
        cache_path = self.cache_dir / filename

        if not cache_path.exists():
            return None

        # Check file age
        file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - file_mtime

        if age > timedelta(days=max_age_days):
            print(f"Cache expired (age: {age.days} days)")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Loaded from cache: {cache_path} (age: {age.days} days)")
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading cache: {e}")
            return None
