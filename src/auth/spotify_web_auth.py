"""Spotify OAuth2 PKCE flow for web apps (Streamlit Cloud compatible).

Instead of a local callback server, this uses redirect-based OAuth:
1. Generate auth URL with app URL as redirect
2. User clicks link, approves in Spotify
3. Spotify redirects back to app with ?code= in query params
4. App exchanges code for tokens
"""

import secrets
import hashlib
import base64
from urllib.parse import urlencode

import requests


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-library-read",
]


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge."""
    code_verifier = secrets.token_urlsafe(64)
    challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def get_auth_url(client_id, redirect_uri, code_challenge, state):
    """Build Spotify authorization URL."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "state": state,
        "scope": " ".join(SCOPES),
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(client_id, redirect_uri, code, code_verifier):
    """Exchange authorization code for access + refresh tokens."""
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    resp = requests.post(SPOTIFY_TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(client_id, refresh_token):
    """Refresh an expired access token."""
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    resp = requests.post(SPOTIFY_TOKEN_URL, data=data)
    resp.raise_for_status()
    token_data = resp.json()
    # Preserve refresh token if Spotify omits it
    if "refresh_token" not in token_data:
        token_data["refresh_token"] = refresh_token
    return token_data
