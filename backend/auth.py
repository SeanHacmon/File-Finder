import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

router = APIRouter()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID", "common")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = "openid profile email offline_access Files.Read Files.Read.All User.Read"

@router.get("/auth/login")
def login():
    auth_url = (
        f"{AUTHORITY}/oauth2/v2.0/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&response_mode=query"
        f"&prompt=select_account"
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
async def auth_callback(request: Request, code: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Auth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": SCOPES,
        })

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {response.text}")

    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    user = await get_user_profile(access_token)

    email = (
        user.get("mail")
        or user.get("userPrincipalName")
        or user.get("email")
        or ""
    )

    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Could not get user ID from Microsoft")

    user_name = user.get("displayName") or user.get("name") or "User"

    # Store in session as backup
    request.session["access_token"] = access_token
    request.session["refresh_token"] = refresh_token or ""
    request.session["user_id"] = user_id
    request.session["user_name"] = user_name
    request.session["user_email"] = email

    print(f"[Auth] User logged in: {email} (id: {user_id})")

    # Pass everything including access token to frontend via URL params
    # Frontend stores in localStorage so it works across all account types
    redirect_url = (
        f"{FRONTEND_URL}/search"
        f"?uid={quote(user_id)}"
        f"&name={quote(user_name)}"
        f"&email={quote(email)}"
        f"&token={quote(access_token)}"
    )
    return RedirectResponse(redirect_url)


@router.get("/auth/me")
def get_me(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": user_id,
        "name": request.session.get("user_name"),
        "email": request.session.get("user_email"),
    }


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}


async def get_user_profile(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
    print(f"[Auth] Graph /me status: {response.status_code}")
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch user profile: {response.text}")
    return response.json()


def get_current_user(request: Request) -> dict:
    """
    Reads user from session OR from Authorization header.
    This supports both cookie-based and token-based auth.
    """
    # Try session first
    user_id = request.session.get("user_id")
    access_token = request.session.get("access_token")

    # Fall back to Authorization header
    if not user_id or not access_token:
        auth_header = request.headers.get("Authorization", "")
        user_id_header = request.headers.get("X-User-Id", "")
        user_name_header = request.headers.get("X-User-Name", "")
        user_email_header = request.headers.get("X-User-Email", "")

        if auth_header.startswith("Bearer ") and user_id_header:
            return {
                "id": user_id_header,
                "name": user_name_header,
                "email": user_email_header,
                "access_token": auth_header.replace("Bearer ", ""),
            }

        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")

    return {
        "id": user_id,
        "name": request.session.get("user_name"),
        "email": request.session.get("user_email"),
        "access_token": access_token,
    }