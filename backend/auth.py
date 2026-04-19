import os
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-min-32-chars")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
ALLOWED_EMAILS = {e.strip() for e in os.getenv("ALLOWED_EMAILS", "").split(",") if e.strip()}

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _make_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=7)
    return jwt.encode({"sub": email, "exp": exp}, SECRET_KEY, algorithm="HS256")


def _decode_token(token: str) -> str | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"]).get("sub")
    except JWTError:
        return None


async def get_current_user(request: Request) -> str:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = _decode_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
    return email


@router.get("/google")
async def login():
    params = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "select_account",
    })
    return RedirectResponse(f"{_AUTH_URL}?{params}")


@router.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        })
        access_token = token_res.json().get("access_token")
        if not access_token:
            raise HTTPException(400, "Token exchange failed — check Google OAuth credentials")

        user_res = await client.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_res.json()

    email = user.get("email", "")
    if email not in ALLOWED_EMAILS:
        raise HTTPException(403, f"Access denied. Contact admin to add {email}.")

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        "session",
        _make_token(email),
        httponly=True,
        samesite="lax",
        max_age=604800,
        secure=REDIRECT_URI.startswith("https"),
    )
    return response


@router.get("/me")
async def me(user: str = Depends(get_current_user)):
    return {"email": user}


@router.post("/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response
