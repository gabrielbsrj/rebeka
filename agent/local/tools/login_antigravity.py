# agent/local/tools/login_antigravity.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-20
# CHANGELOG: Criação — Fluxo OAuth 2.0 PKCE para Google Antigravity

import hashlib
import secrets
import webbrowser
import logging
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from threading import Thread, Event
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

# ─── OAuth Credentials ───
# Configure via environment variables or replace with your own
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "YOUR_CLIENT_ID.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:51121/oauth-callback"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo?alt=json"
CODE_ASSIST_URL = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
DEFAULT_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "your-project-id")
DEFAULT_MODEL = "google-antigravity/claude-opus-4-6-thinking"

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

# ─── Estado global do OAuth callback ───
_oauth_result: Dict[str, str] = {}
_oauth_done = Event()


def _generate_pkce() -> tuple[str, str]:
    """Gera verifier e challenge PKCE (S256)."""
    verifier = secrets.token_hex(32)
    challenge = (
        hashlib.sha256(verifier.encode("ascii"))
        .digest()
    )
    # base64url encoding (sem padding)
    import base64
    challenge_b64 = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii")
    return verifier, challenge_b64


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler HTTP mínimo para capturar o callback do OAuth."""

    def do_GET(self):
        global _oauth_result
        parsed = urlparse(self.path)

        if parsed.path != "/oauth-callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if code:
            _oauth_result = {"code": code, "state": state or ""}
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Login concluido!</h1>"
                b"<p>Pode fechar esta aba e voltar para a Rebeka.</p>"
                b"</body></html>"
            )
        else:
            error = params.get("error", ["unknown"])[0]
            _oauth_result = {"error": error}
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<html><body><h1>Erro: {error}</h1></body></html>".encode())

        _oauth_done.set()

    def log_message(self, format, *args):
        # Silencia logs do servidor HTTP
        pass


def _exchange_code(code: str, verifier: str) -> Dict[str, Any]:
    """Troca o authorization code por tokens de acesso."""
    response = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    })

    if response.status_code != 200:
        raise RuntimeError(f"Token exchange failed ({response.status_code}): {response.text}")

    data = response.json()
    access_token = data.get("access_token", "").strip()
    refresh_token = data.get("refresh_token", "").strip()
    expires_in = data.get("expires_in", 0)

    if not access_token:
        raise RuntimeError("Token exchange returned no access_token")

    import time
    expires_at = time.time() + expires_in - 300  # 5min buffer

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def _fetch_user_email(access_token: str) -> Optional[str]:
    """Busca o email do usuário autenticado."""
    try:
        r = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code == 200:
            return r.json().get("email")
    except Exception:
        pass
    return None


def _fetch_project_id(access_token: str) -> str:
    """Descobre o project ID via Cloud Code Assist API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "google-api-nodejs-client/9.15.1",
        "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    }
    body = {
        "metadata": {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
        }
    }

    endpoints = [
        "https://cloudcode-pa.googleapis.com",
        "https://daily-cloudcode-pa.sandbox.googleapis.com",
    ]

    for endpoint in endpoints:
        try:
            r = requests.post(
                f"{endpoint}/v1internal:loadCodeAssist",
                headers=headers,
                json=body,
                timeout=10,
            )
            if r.status_code != 200:
                continue

            data = r.json()
            project = data.get("cloudaicompanionProject")
            if isinstance(project, str) and project.strip():
                return project
            if isinstance(project, dict) and project.get("id"):
                return project["id"]
        except Exception:
            continue

    return DEFAULT_PROJECT_ID


def perform_google_login(timeout_seconds: int = 300) -> Dict[str, Any]:
    """
    Executa o fluxo completo de login OAuth 2.0 com PKCE para o Google Antigravity.

    1. Gera PKCE verifier/challenge.
    2. Inicia servidor HTTP local na porta 51121.
    3. Abre o navegador com a URL de autenticação do Google.
    4. Aguarda o callback com o authorization code.
    5. Troca o code por tokens.
    6. Busca email e project ID.

    Returns:
        Dict com access_token, refresh_token, expires_at, email, project_id.
    """
    global _oauth_result, _oauth_done
    _oauth_result = {}
    _oauth_done.clear()

    verifier, challenge = _generate_pkce()
    state = secrets.token_hex(16)

    # Construir URL de autenticação
    auth_params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    # Iniciar servidor HTTP local
    server = HTTPServer(("127.0.0.1", 51121), _OAuthCallbackHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    logger.info("Servidor OAuth iniciado em http://localhost:51121")
    logger.info(f"Abrindo navegador para autenticação Google...")

    # Abrir navegador
    webbrowser.open(auth_url)

    # Aguardar callback
    got_callback = _oauth_done.wait(timeout=timeout_seconds)
    server.shutdown()

    if not got_callback:
        raise TimeoutError("Tempo limite de autenticação excedido. Tente novamente.")

    if "error" in _oauth_result:
        raise RuntimeError(f"Erro no OAuth: {_oauth_result['error']}")

    if _oauth_result.get("state") != state:
        raise RuntimeError("Erro de segurança: state mismatch no OAuth.")

    # Trocar code por tokens
    logger.info("Trocando authorization code por tokens...")
    tokens = _exchange_code(_oauth_result["code"], verifier)

    # Buscar informações adicionais
    email = _fetch_user_email(tokens["access_token"])
    project_id = _fetch_project_id(tokens["access_token"])

    logger.info(f"Login Antigravity concluído! Email: {email}, Projeto: {project_id}")

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_at": tokens["expires_at"],
        "email": email,
        "project_id": project_id,
        "default_model": DEFAULT_MODEL,
    }
