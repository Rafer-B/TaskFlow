import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "development-secret-change-before-deploy")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7

# A palavra-passe é derivada com PBKDF2 e sal aleatório; armazenam-se o sal e
# o resultado codificados, nunca a palavra-passe original.
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


# Ao validar, recalcula-se o hash com o sal guardado; `compare_digest` evita
# comparação simples que possa revelar informação pelo tempo de resposta.
def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_text, digest_text = stored_hash.split("$", maxsplit=1)
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hmac.compare_digest(actual, expected)


# O token proprietário contém um payload codificado e uma assinatura HMAC-SHA256,
# permitindo validar a identidade e a integridade sem confiar no payload isolado.
def create_access_token(user_id: int) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}).encode()
    ).rstrip(b"=")
    signature = hmac.new(TOKEN_SECRET.encode(), payload, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{payload.decode()}.{encoded_signature.decode()}"


# A validacao do token verifica a assinatura e expiracao antes de devolver o
# `sub`, preservando a sessao apenas enquanto o token for valido.
def get_user_id_from_token(token: str) -> int:
    try:
        payload_text, signature_text = token.split(".", maxsplit=1)
        payload = payload_text.encode()
        signature = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        expected = hmac.new(TOKEN_SECRET.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        data = json.loads(
            base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4))
        )
        user_id = int(data["sub"])
        if int(data["exp"]) <= int(time.time()):
            raise ValueError("Expired token")
        return user_id
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
