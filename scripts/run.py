"""Music Taste Genome -- CLI entry point."""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(project_root / ".env")


def cmd_auth(args):
    """Run Spotify OAuth setup."""
    from src.auth.spotify_auth import SpotifyAuthenticator

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

    if not client_id:
        print("ERROR: SPOTIFY_CLIENT_ID not set in .env file.")
        print("Get one from https://developer.spotify.com/dashboard")
        print("Then add it to your .env file.")
        sys.exit(1)

    auth = SpotifyAuthenticator(client_id, redirect_uri)
    auth.run_auth_flow()
    print("Authentication complete! Token cached.")


def cmd_collect(args):
    """Collect Spotify listening data."""
    from src.auth.spotify_auth import SpotifyAuthenticator
    from src.collectors.spotify_collector import SpotifyCollector

    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

    if not client_id:
        print("ERROR: SPOTIFY_CLIENT_ID not set in .env file.")
        sys.exit(1)

    auth = SpotifyAuthenticator(client_id, redirect_uri)
    token = auth.get_valid_token()
    if not token:
        print("ERROR: No valid token. Run 'auth' first.")
        sys.exit(1)

    collector = SpotifyCollector(auth)
    data = collector.collect_full_profile(saved_limit=args.limit)

    print(f"\nCollection complete:")
    print(f"  Total unique tracks: {data.get('total_unique_tracks', 0)}")
    print(f"  Unique artists: {len(data.get('unique_artists', []))}")
    print(f"  Cached to: data/cache/spotify_collection.json")


def cmd_analyze(args):
    """Analyze sonic DNA and generate report."""
    import json
    from src.analyzers.sonic_profiler import build_sonic_dna
    from src.analyzers.temporal_analyzer import analyze_temporal_patterns
    from src.genome_linker import build_genome_context
    from src.correlator import GenomeMusicCorrelator
    from src.reporter import generate_report, export_sonic_dna_json

    # Load collected Spotify data
    cache_path = project_root / "data" / "cache" / "spotify_collection.json"
    if not cache_path.exists():
        print("ERROR: No Spotify data found. Run 'collect' first.")
        sys.exit(1)

    with open(cache_path, "r", encoding="utf-8") as f:
        collection = json.load(f)

    tracks = collection.get("tracks", [])
    if not tracks:
        print("ERROR: No tracks in collection. Run 'collect' first.")
        sys.exit(1)

    print(f"Loaded {len(tracks)} tracks from cache.")

    # Build sonic DNA
    print("Building sonic DNA profile...")
    sonic_dna = build_sonic_dna(tracks)
    print(f"  Signature: {', '.join(d.get('label', '?') for d in sonic_dna.get('signature', {}).values())}")

    # Temporal analysis (from recently played tracks with timestamps)
    timestamped = [t for t in tracks if t.get("played_at")]
    temporal = None
    if timestamped:
        print(f"Analyzing temporal patterns ({len(timestamped)} timestamped tracks)...")
        temporal = analyze_temporal_patterns(timestamped)

    # Genome correlations
    correlations = []
    if args.genome:
        print(f"Loading genome data from {args.genome}...")
        genome_context = build_genome_context(args.genome, args.circadian)
        available = genome_context.get("available_correlations", [])
        print(f"  Found {len(genome_context.get('genes', {}))} relevant genes")
        print(f"  Available correlations: {len(available)}")

        if available:
            correlator = GenomeMusicCorrelator(sonic_dna, genome_context, temporal)
            correlations = correlator.run_all()
            print(f"  Computed {len(correlations)} correlations")
    else:
        print("No genome data provided. Skipping correlations.")

    # Generate report
    print(f"\nGenerating report...")
    generate_report(sonic_dna, correlations, temporal, args.out)

    # Export JSON
    json_out = str(Path(args.out).parent / "sonic_dna.json")
    export_sonic_dna_json(sonic_dna, correlations, temporal, json_out)

    print("\nDone!")


def cmd_full(args):
    """End-to-end: collect + analyze + report."""
    # Collect
    print("=== STEP 1: Collecting Spotify data ===\n")
    cmd_collect(args)

    # Analyze
    print("\n=== STEP 2: Analyzing + generating report ===\n")
    cmd_analyze(args)


def main():
    parser = argparse.ArgumentParser(
        description="Music Taste Genome -- Map your Spotify DNA against your actual genome"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # auth
    subparsers.add_parser("auth", help="Setup Spotify authentication (one-time)")

    # collect
    collect_p = subparsers.add_parser("collect", help="Collect Spotify listening data")
    collect_p.add_argument("--limit", type=int, default=500, help="Max saved tracks to fetch")

    # analyze
    analyze_p = subparsers.add_parser("analyze", help="Analyze sonic DNA and generate report")
    analyze_p.add_argument("--genome", help="Path to genome-insight findings.json")
    analyze_p.add_argument("--circadian", help="Path to circadian_profile.json (optional)")
    analyze_p.add_argument("--out", default="reports/music_taste_genome_report.md",
                           help="Output report path")

    # full
    full_p = subparsers.add_parser("full", help="Collect + Analyze + Report (end-to-end)")
    full_p.add_argument("--genome", help="Path to genome-insight findings.json")
    full_p.add_argument("--circadian", help="Path to circadian_profile.json (optional)")
    full_p.add_argument("--out", default="reports/music_taste_genome_report.md",
                        help="Output report path")
    full_p.add_argument("--limit", type=int, default=500, help="Max saved tracks to fetch")

    args = parser.parse_args()

    if args.command == "auth":
        cmd_auth(args)
    elif args.command == "collect":
        cmd_collect(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "full":
        cmd_full(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
