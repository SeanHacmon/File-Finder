from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
import os

from auth import router as auth_router, get_current_user
from database import init_db, search_files
from indexer import index_user_files, get_progress

load_dotenv()

# ── Startup ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database ready")
    yield

app = FastAPI(title="OneDrive Smart Search", lifespan=lifespan)

# ── Middleware ────────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "fallback-secret-change-this")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth_router)


# ── Health ────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "OneDrive Smart Search API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}


# ── Indexing ──────────────────────────────────────────────────────
@app.post("/index")
async def trigger_index(user=Depends(get_current_user)):
    """
    Triggers background indexing of the user's OneDrive files.
    Called automatically after login.
    """
    asyncio.create_task(
        index_user_files(user["id"], user["access_token"])
    )
    return {"status": "indexing_started"}


@app.get("/index/progress")
def index_progress(user=Depends(get_current_user)):
    """
    Returns the current indexing progress for the logged-in user.
    Frontend polls this every few seconds to update the progress bar.
    """
    return get_progress(user["id"])


# ── Search ────────────────────────────────────────────────────────
@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Keywords to search for"),
    limit: int = Query(10, ge=1, le=50),
    user=Depends(get_current_user)
):
    """
    Searches the user's indexed files using SQLite FTS5 keyword matching.
    Returns ranked results with filename, path, type, snippet and OneDrive link.
    """
    if not q.strip():
        return {"results": [], "query": q}

    # Format query for FTS5 — wrap each word with quotes for exact matching
    fts_query = " AND ".join(f'"{word}"' for word in q.strip().split())

    try:
        results = search_files(user["id"], fts_query, limit)
        return {
            "query": q,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        # If FTS query syntax is invalid, fall back to simple search
        try:
            results = search_files(user["id"], q, limit)
            return {
                "query": q,
                "count": len(results),
                "results": results
            }
        except Exception as e2:
            return {"query": q, "count": 0, "results": [], "error": str(e2)}