import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID", "common")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")

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

    # Personal accounts may not have "mail" — try multiple fields
    email = (
        user.get("mail")
        or user.get("userPrincipalName")
        or user.get("email")
        or ""
    )

    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Could not get user ID from Microsoft")

    request.session["access_token"] = access_token
    request.session["refresh_token"] = refresh_token or ""
    request.session["user_id"] = user_id
    request.session["user_name"] = user.get("displayName") or user.get("name") or "User"
    request.session["user_email"] = email

    print(f"[Auth] User logged in: {email} (id: {user_id})")

    return RedirectResponse("http://localhost:3000/search")

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
    print(f"[Auth] Graph /me response: {response.text[:500]}")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch user profile: {response.text}")
    return response.json()

def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    return {
        "id": user_id,
        "name": request.session.get("user_name"),
        "email": request.session.get("user_email"),
        "access_token": request.session.get("access_token"),
    }