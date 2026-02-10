"""Music Taste Genome -- Streamlit Web App.

Map your Spotify listening patterns against your actual genome.
"""

import json
import secrets

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src.auth.spotify_web_auth import (
    generate_pkce_pair,
    get_auth_url,
    exchange_code_for_token,
)
from src.collectors.spotify_collector import SpotifyCollector
from src.analyzers.sonic_profiler import build_sonic_dna
from src.analyzers.temporal_analyzer import analyze_temporal_patterns
from src.genome_linker import build_genome_context
from src.correlator import GenomeMusicCorrelator

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Music Taste Genome",
    page_icon="::dna::",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Secrets / config
# ---------------------------------------------------------------------------
CLIENT_ID = st.secrets.get("SPOTIFY_CLIENT_ID", "")
# Build redirect URI from the app's own URL
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501")


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "access_token": None,
        "refresh_token": None,
        "code_verifier": None,
        "auth_state": None,
        "spotify_data": None,
        "sonic_dna": None,
        "temporal": None,
        "correlations": None,
        "genome_context": None,
        "step": "connect",  # connect -> collecting -> results
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_state()

# ---------------------------------------------------------------------------
# Handle OAuth callback (runs on every page load)
# ---------------------------------------------------------------------------
query_params = st.query_params
auth_code = query_params.get("code")
returned_state = query_params.get("state")

if auth_code and st.session_state.access_token is None:
    # We got a callback from Spotify
    if st.session_state.code_verifier:
        try:
            token_data = exchange_code_for_token(
                CLIENT_ID,
                REDIRECT_URI,
                auth_code,
                st.session_state.code_verifier,
            )
            st.session_state.access_token = token_data["access_token"]
            st.session_state.refresh_token = token_data.get("refresh_token")
            st.session_state.step = "collecting"
            # Clear query params
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("Music Taste Genome")
    st.caption("Your Spotify DNA x Your Actual DNA")

    st.divider()

    if st.session_state.access_token:
        st.success("Spotify connected")
        if st.button("Disconnect Spotify"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.info("Connect Spotify to begin")

    st.divider()

    # Genome data upload
    st.subheader("Genome Data (optional)")
    genome_file = st.file_uploader(
        "Upload findings.json from genome-insight",
        type=["json"],
        key="genome_upload",
    )
    circadian_file = st.file_uploader(
        "Upload circadian_profile.json (optional)",
        type=["json"],
        key="circadian_upload",
    )

    st.divider()
    st.caption(
        "This is entertainment, not science. "
        "Gene-music correlations are speculative. "
        "Your genome is not your destiny."
    )

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if st.session_state.step == "connect" and st.session_state.access_token is None:
    # ---- Step 1: Connect Spotify ----
    st.header("Welcome to Music Taste Genome")
    st.write(
        "Connect your Spotify account to map your listening patterns against "
        "audio features and discover your **sonic DNA**. Optionally upload your "
        "genome data to cross-reference with your actual genes."
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if not CLIENT_ID:
            st.error(
                "SPOTIFY_CLIENT_ID not configured. "
                "Add it to .streamlit/secrets.toml or Streamlit Cloud secrets."
            )
        else:
            # Generate PKCE pair and auth URL
            code_verifier, code_challenge = generate_pkce_pair()
            state = secrets.token_urlsafe(16)
            st.session_state.code_verifier = code_verifier
            st.session_state.auth_state = state

            auth_url = get_auth_url(CLIENT_ID, REDIRECT_URI, code_challenge, state)

            st.link_button(
                "Connect Spotify",
                auth_url,
                use_container_width=True,
                type="primary",
            )
            st.caption("Opens Spotify login. We only read your listening history.")

    # Show what the app does
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Sonic DNA")
        st.write(
            "Aggregate your audio features (tempo, energy, valence, "
            "danceability) into a musical personality profile."
        )
    with col2:
        st.subheader("Listening Patterns")
        st.write(
            "When do you listen? How does your music shift "
            "from morning to evening?"
        )
    with col3:
        st.subheader("Genome Crossref")
        st.write(
            "Upload genome findings to see speculative correlations: "
            "caffeine metabolism x BPM, chronotype x listening hours, and more."
        )


elif st.session_state.step == "collecting":
    # ---- Step 2: Collect data ----
    st.header("Collecting your Spotify data...")

    progress = st.progress(0, text="Starting collection...")

    try:
        collector = SpotifyCollector(access_token=st.session_state.access_token)

        progress.progress(10, text="Fetching recently played...")
        recently = collector.get_recently_played(limit=50)

        progress.progress(25, text="Fetching top tracks (short term)...")
        top_short = collector.get_top_tracks("short_term", 50)

        progress.progress(40, text="Fetching top tracks (medium term)...")
        top_medium = collector.get_top_tracks("medium_term", 50)

        progress.progress(55, text="Fetching top tracks (long term)...")
        top_long = collector.get_top_tracks("long_term", 50)

        progress.progress(65, text="Fetching saved library...")
        saved = collector.get_saved_tracks(limit=200)

        # Deduplicate
        all_tracks = recently + top_short + top_medium + top_long + saved
        seen = set()
        unique_tracks = []
        for t in all_tracks:
            if t["track_id"] not in seen:
                seen.add(t["track_id"])
                unique_tracks.append(t)

        progress.progress(80, text=f"Fetching audio features for {len(unique_tracks)} tracks...")
        track_ids = [t["track_id"] for t in unique_tracks]
        audio_features = collector.get_audio_features(track_ids)

        # Merge features
        for track in unique_tracks:
            features = audio_features.get(track["track_id"])
            track["audio_features"] = features if features else None

        # Filter tracks with features
        tracks_with_features = [t for t in unique_tracks if t.get("audio_features")]

        progress.progress(90, text="Building sonic DNA...")

        # Build sonic DNA
        sonic_dna = build_sonic_dna(tracks_with_features)

        # Temporal analysis
        timestamped = [t for t in tracks_with_features if t.get("played_at")]
        temporal = analyze_temporal_patterns(timestamped) if timestamped else None

        # Process genome data if uploaded
        genome_context = None
        correlations = []
        if genome_file is not None:
            import tempfile, os
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                f.write(genome_file.getvalue().decode("utf-8"))
                findings_path = f.name

            circadian_path = None
            if circadian_file is not None:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                    f.write(circadian_file.getvalue().decode("utf-8"))
                    circadian_path = f.name

            genome_context = build_genome_context(findings_path, circadian_path)
            correlator = GenomeMusicCorrelator(sonic_dna, genome_context, temporal)
            correlations = correlator.run_all()

            os.unlink(findings_path)
            if circadian_path:
                os.unlink(circadian_path)

        # Store in session
        st.session_state.spotify_data = {
            "tracks": tracks_with_features,
            "total": len(unique_tracks),
            "with_features": len(tracks_with_features),
        }
        st.session_state.sonic_dna = sonic_dna
        st.session_state.temporal = temporal
        st.session_state.genome_context = genome_context
        st.session_state.correlations = correlations
        st.session_state.step = "results"

        progress.progress(100, text="Done!")
        st.rerun()

    except Exception as e:
        st.error(f"Collection failed: {e}")
        if st.button("Try again"):
            st.session_state.step = "connect"
            st.session_state.access_token = None
            st.rerun()


elif st.session_state.step == "results":
    # ---- Step 3: Results ----
    sonic = st.session_state.sonic_dna
    temporal = st.session_state.temporal
    correlations = st.session_state.correlations or []
    data = st.session_state.spotify_data

    # Header metrics
    st.header("Your Music Taste Genome")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tracks Analyzed", data["with_features"])
    col2.metric("Unique Artists", sonic.get("unique_artists", 0))
    col3.metric("Diversity Index", f"{sonic.get('diversity', {}).get('diversity_index', 0)}/100")
    col4.metric("Genome Correlations", len(correlations))

    st.divider()

    # ---- Sonic DNA Signature ----
    st.subheader("Your Sonic DNA Signature")
    signature = sonic.get("signature", {})

    sig_cols = st.columns(5)
    dim_icons = {
        "emotional_tone": "Emotional Tone",
        "energy_level": "Energy Level",
        "musical_complexity": "Musical Complexity",
        "tempo_preference": "Tempo Preference",
        "diversity": "Diversity",
    }
    for i, (key, display_name) in enumerate(dim_icons.items()):
        dim = signature.get(key, {})
        with sig_cols[i]:
            val = dim.get("value", 0)
            label = dim.get("label", "?")
            if key == "tempo_preference":
                st.metric(display_name, f"{val:.0f} BPM", label)
            elif key == "diversity":
                st.metric(display_name, f"{val}/100", label)
            else:
                st.metric(display_name, f"{val:.2f}", label)

    st.divider()

    # ---- Audio Features ----
    tab_features, tab_temporal, tab_genome = st.tabs([
        "Audio Features",
        "Listening Patterns",
        "Genome x Music",
    ])

    with tab_features:
        features = sonic.get("audio_features", {})

        # Radar chart of core features
        feature_names = ["Energy", "Valence", "Danceability", "Acousticness", "Instrumentalness", "Speechiness", "Liveness"]
        feature_keys = ["energy", "valence", "danceability", "acousticness", "instrumentalness", "speechiness", "liveness"]
        values = [features.get(k, {}).get("median", 0) for k in feature_keys]

        fig_radar = go.Figure(data=go.Scatterpolar(
            r=values + [values[0]],  # close the shape
            theta=feature_names + [feature_names[0]],
            fill="toself",
            fillcolor="rgba(29, 185, 84, 0.3)",
            line=dict(color="#1DB954", width=2),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
            title="Audio Feature Radar",
            height=450,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Feature distributions
        col_left, col_right = st.columns(2)

        with col_left:
            # Tempo distribution
            tempo = features.get("tempo", {})
            if tempo:
                st.metric("Tempo", f"{tempo.get('median', 0):.0f} BPM",
                          f"Range: {tempo.get('min', 0):.0f} - {tempo.get('max', 0):.0f}")

            # Mode split
            mode = features.get("mode_split", {})
            if mode:
                fig_mode = go.Figure(data=go.Pie(
                    labels=["Major", "Minor"],
                    values=[mode.get("major", 0), mode.get("minor", 0)],
                    marker_colors=["#1DB954", "#535353"],
                    hole=0.4,
                ))
                fig_mode.update_layout(title="Major vs Minor", height=300)
                st.plotly_chart(fig_mode, use_container_width=True)

        with col_right:
            # Key distribution
            key_dist = features.get("key_distribution", {})
            if key_dist:
                fig_keys = go.Figure(data=go.Bar(
                    x=list(key_dist.keys()),
                    y=list(key_dist.values()),
                    marker_color="#1DB954",
                ))
                fig_keys.update_layout(
                    title="Key Distribution",
                    xaxis_title="Key",
                    yaxis_title="Frequency",
                    height=350,
                )
                st.plotly_chart(fig_keys, use_container_width=True)

        # Top artists
        top_artists = sonic.get("top_artists", [])
        if top_artists:
            st.subheader("Top Artists")
            artist_cols = st.columns(min(5, len(top_artists)))
            for i, artist in enumerate(top_artists[:5]):
                name = artist if isinstance(artist, str) else artist.get("name", "?")
                with artist_cols[i]:
                    st.write(f"**{i+1}.** {name}")

    with tab_temporal:
        if temporal and temporal.get("total_tracks_with_timestamps", 0) > 0:
            st.subheader("When You Listen")
            st.caption(f"Based on {temporal['total_tracks_with_timestamps']} recently played tracks")

            # 24-hour timeline
            hours = list(range(24))
            counts = temporal.get("hour_distribution", [0] * 24)
            peak = temporal.get("peak_hour")

            colors = ["#1DB954" if h == peak else "#535353" for h in hours]

            fig_hours = go.Figure(data=go.Bar(
                x=[f"{h:02d}:00" for h in hours],
                y=counts,
                marker_color=colors,
            ))
            fig_hours.update_layout(
                title="Listening by Hour of Day",
                xaxis_title="Hour",
                yaxis_title="Tracks",
                height=350,
            )
            st.plotly_chart(fig_hours, use_container_width=True)

            if peak is not None:
                st.info(f"Peak listening hour: **{peak:02d}:00**")

            # Morning vs evening shift
            shift = temporal.get("circadian_shift")
            if shift:
                st.subheader("Morning vs Evening Shift")
                morning = temporal.get("morning_avg_features", {})
                evening = temporal.get("evening_avg_features", {})

                sc1, sc2, sc3 = st.columns(3)
                if morning and evening:
                    td = shift.get("tempo_delta", 0)
                    ed = shift.get("energy_delta", 0)
                    vd = shift.get("valence_delta", 0)
                    sc1.metric("Tempo Shift", f"{'+' if td >= 0 else ''}{td:.0f} BPM",
                               f"AM: {morning.get('tempo', 0):.0f} / PM: {evening.get('tempo', 0):.0f}")
                    sc2.metric("Energy Shift", f"{'+' if ed >= 0 else ''}{ed:.2f}",
                               f"AM: {morning.get('energy', 0):.2f} / PM: {evening.get('energy', 0):.2f}")
                    sc3.metric("Valence Shift", f"{'+' if vd >= 0 else ''}{vd:.2f}",
                               f"AM: {morning.get('valence', 0):.2f} / PM: {evening.get('valence', 0):.2f}")
        else:
            st.info("No timestamped tracks available for temporal analysis.")

    with tab_genome:
        if correlations:
            st.subheader("Genome x Music Correlations")
            st.warning(
                "These are speculative hypotheses based on loose neuroscience. "
                "Your genes are not your destiny, and your Spotify history is not your genome. "
                "This is for fun."
            )

            for corr in correlations:
                with st.expander(
                    f"{corr['gene']} x {corr['metric']} -- {corr['confidence'].upper()}",
                    expanded=False,
                ):
                    gcol1, gcol2 = st.columns([1, 2])
                    with gcol1:
                        st.write(f"**Gene:** {corr['gene']}")
                        st.write(f"**Status:** {corr['gene_status']}")
                        st.write(f"**Your value:** {corr['value']}")
                        st.write(f"**Confidence:** {corr['confidence'].upper()}")
                    with gcol2:
                        st.write(f"**Verdict:** {corr['verdict']}")

                    st.divider()

                    mcol1, mcol2 = st.columns(2)
                    with mcol1:
                        st.write("**Why this might matter:**")
                        st.write(corr["why_matters"])
                    with mcol2:
                        st.write("**Why this might be BS:**")
                        st.write(corr["why_bs"])

                    # Expected ranges
                    expected = corr.get("expected_ranges", {})
                    if expected:
                        st.write("**Expected ranges:**")
                        range_text = []
                        for status, rng in expected.items():
                            if isinstance(rng, dict):
                                range_text.append(f"- {status}: {rng.get('min', '?')} - {rng.get('max', '?')}")
                            else:
                                range_text.append(f"- {status}: {rng}")
                        st.write("\n".join(range_text))

        else:
            st.subheader("Genome x Music Correlations")
            st.info(
                "Upload your **findings.json** from the genome-insight pipeline "
                "in the sidebar to see speculative correlations between your genes "
                "and your music taste."
            )
            st.write("**Available correlations when genome data is provided:**")
            st.write(
                "1. **CYP1A2 x Tempo** -- Caffeine metabolism vs BPM preference\n"
                "2. **Chronotype x Listening Hours** -- Morning/evening type alignment\n"
                "3. **COMT x Valence** -- Dopamine metabolism vs positivity in music\n"
                "4. **BDNF x Diversity** -- Neuroplasticity vs genre exploration\n"
                "5. **SLC6A4 x Emotional Range** -- Serotonin vs valence variance\n"
                "6. **DRD2 x Repeat Plays** -- Dopamine receptor vs replay behavior\n"
                "7. **OPRM1 x Sad Music** -- Opioid receptor vs melancholic preference"
            )

    # ---- Rerun button ----
    st.divider()
    rc1, rc2, rc3 = st.columns([1, 1, 1])
    with rc2:
        if st.button("Re-analyze with genome data", use_container_width=True):
            st.session_state.step = "collecting"
            st.rerun()

    # ---- Export ----
    with st.expander("Export Data"):
        export = {
            "sonic_dna": sonic,
            "temporal_patterns": temporal,
            "genome_correlations": correlations,
        }
        st.download_button(
            "Download Sonic DNA (JSON)",
            json.dumps(export, indent=2, default=str),
            "sonic_dna.json",
            "application/json",
        )
