"""Spotify OAuth2 PKCE authentication flow with local callback server."""

import json
import secrets
import hashlib
import base64
import webbrowser
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Optional
from datetime import datetime, timedelta

import requests


class SpotifyAuthenticator:
    """Spotify OAuth2 PKCE flow with local callback server."""

    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id: str, redirect_uri: str = "http://localhost:8888/callback"):
        """
        Initialize Spotify authenticator.

        Args:
            client_id: Spotify application client ID
            redirect_uri: OAuth callback URI (must match Spotify app settings)
        """
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.token_cache_path = Path("data/cache/.spotify_token.json")
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """
        Generate PKCE code_verifier and code_challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate cryptographically secure random verifier
        code_verifier = secrets.token_urlsafe(64)

        # Create challenge from verifier using SHA256
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def get_auth_url(self) -> tuple[str, str, str]:
        """
        Generate Spotify authorization URL with PKCE parameters.

        Returns:
            Tuple of (auth_url, code_verifier, state)
        """
        code_verifier, code_challenge = self._generate_pkce_pair()
        state = secrets.token_urlsafe(16)

        # Required scopes for listening history and library access
        scopes = [
            "user-read-recently-played",
            "user-top-read",
            "user-library-read"
        ]

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
            "state": state,
            "scope": " ".join(scopes)
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        return auth_url, code_verifier, state

    def exchange_code(self, code: str, code_verifier: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            Token data dictionary

        Raises:
            requests.HTTPError: If token exchange fails
        """
        data = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier
        }

        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()

        token_data = response.json()

        # Add expiry timestamp
        token_data["expires_at"] = (
            datetime.now() + timedelta(seconds=token_data["expires_in"])
        ).isoformat()

        self._save_token(token_data)
        return token_data

    def refresh_token(self) -> str:
        """
        Refresh expired access token using refresh_token.

        Returns:
            New access token

        Raises:
            ValueError: If no cached token or refresh token unavailable
            requests.HTTPError: If refresh fails
        """
        cached_token = self._load_token()
        if not cached_token or "refresh_token" not in cached_token:
            raise ValueError("No refresh token available. Re-authentication required.")

        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": cached_token["refresh_token"]
        }

        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()

        token_data = response.json()

        # Preserve refresh token if not returned (Spotify sometimes omits it)
        if "refresh_token" not in token_data:
            token_data["refresh_token"] = cached_token["refresh_token"]

        # Add expiry timestamp
        token_data["expires_at"] = (
            datetime.now() + timedelta(seconds=token_data["expires_in"])
        ).isoformat()

        self._save_token(token_data)
        return token_data["access_token"]

    def get_valid_token(self) -> str:
        """
        Get valid access token (refresh if expired, prompt re-auth if no token).

        Returns:
            Valid access token
        """
        cached_token = self._load_token()

        if not cached_token:
            print("No cached token found. Running authentication flow...")
            self.run_auth_flow()
            cached_token = self._load_token()

        # Check if token is expired or will expire within 5 minutes
        expires_at = datetime.fromisoformat(cached_token["expires_at"])
        if datetime.now() >= expires_at - timedelta(minutes=5):
            print("Token expired or expiring soon. Refreshing...")
            try:
                return self.refresh_token()
            except Exception as e:
                print(f"Token refresh failed: {e}")
                print("Running full authentication flow...")
                self.run_auth_flow()
                cached_token = self._load_token()

        return cached_token["access_token"]

    def _save_token(self, token_data: dict):
        """Save token data to cache file."""
        with open(self.token_cache_path, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)
        print(f"Token saved to {self.token_cache_path}")

    def _load_token(self) -> Optional[dict]:
        """Load cached token data."""
        if not self.token_cache_path.exists():
            return None

        try:
            with open(self.token_cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def run_auth_flow(self):
        """
        Run interactive OAuth flow: open browser, start local server, wait for callback.

        This method:
        1. Generates PKCE parameters
        2. Opens browser to Spotify authorization page
        3. Starts local HTTP server to receive callback
        4. Exchanges authorization code for tokens
        5. Saves tokens to cache
        """
        # Generate auth URL and PKCE parameters
        auth_url, code_verifier, state = self.get_auth_url()

        # Parse redirect URI to get port
        parsed_uri = urlparse(self.redirect_uri)
        port = parsed_uri.port or 8888

        # Shared state between handler and main thread
        callback_result = {}

        class CallbackHandler(BaseHTTPRequestHandler):
            """Handle OAuth callback request."""

            def do_GET(self):
                """Handle GET request with authorization code."""
                # Parse query parameters
                parsed_path = urlparse(self.path)
                params = parse_qs(parsed_path.query)

                # Check for error
                if "error" in params:
                    error = params["error"][0]
                    self.send_error(400, f"Authorization failed: {error}")
                    callback_result["error"] = error
                    return

                # Validate state parameter
                if "state" not in params or params["state"][0] != state:
                    self.send_error(400, "Invalid state parameter")
                    callback_result["error"] = "invalid_state"
                    return

                # Extract authorization code
                if "code" not in params:
                    self.send_error(400, "No authorization code received")
                    callback_result["error"] = "no_code"
                    return

                callback_result["code"] = params["code"][0]

                # Send success response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Spotify Authentication Success</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background-color: #1DB954;
                            color: white;
                        }
                        .container {
                            text-align: center;
                        }
                        h1 { font-size: 3em; margin-bottom: 20px; }
                        p { font-size: 1.2em; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Success!</h1>
                        <p>Authentication complete. You can close this tab.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode('utf-8'))

            def log_message(self, format, *args):
                """Suppress default request logging."""
                pass

        # Start local server
        server = HTTPServer(('localhost', port), CallbackHandler)

        print(f"Starting local callback server on port {port}...")
        print(f"Opening browser for Spotify authorization...")
        print(f"If browser doesn't open, visit: {auth_url}")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback (timeout after 5 minutes)
        start_time = time.time()
        timeout = 300  # 5 minutes

        while not callback_result and (time.time() - start_time) < timeout:
            server.handle_request()

        server.server_close()

        # Check result
        if "error" in callback_result:
            raise RuntimeError(f"Authentication failed: {callback_result['error']}")

        if "code" not in callback_result:
            raise RuntimeError("Authentication timeout or no code received")

        # Exchange code for tokens
        print("Authorization code received. Exchanging for tokens...")
        self.exchange_code(callback_result["code"], code_verifier)
        print("Authentication successful!")
