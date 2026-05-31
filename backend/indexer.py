import httpx
import asyncio
from extractor import extract_text, SUPPORTED_TYPES
from database import upsert_file, get_indexed_file_ids
import os

# Max file size we will download and index (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Global dictionary to track indexing progress per user
# { user_id: { "total": 100, "done": 45, "status": "indexing" } }
indexing_progress = {}

def get_progress(user_id: str):
    return indexing_progress.get(user_id, {
        "status": "not_started",
        "total": 0,
        "done": 0,
        "percent": 0
    })

async def index_user_files(user_id: str, access_token: str):
    """
    Main indexing function — runs in the background after login.
    Step 1: Fetch all file metadata from OneDrive (fast, no downloads)
    Step 2: Filter to supported types and size limit
    Step 3: Download and index each file one by one
    """
    indexing_progress[user_id] = {
        "status": "fetching",
        "total": 0,
        "done": 0,
        "percent": 0
    }

    try:
        # Step 1: Fetch all files metadata from OneDrive
        print(f"[Indexer] Fetching file list for user {user_id}...")
        all_files = await fetch_all_files(access_token)
        print(f"[Indexer] Found {len(all_files)} total files in OneDrive")

        # Step 2: Filter to supported types and under size limit
        supported_files = [
            f for f in all_files
            if get_extension(f.get("name", "")) in SUPPORTED_TYPES
            and f.get("size", 0) <= MAX_FILE_SIZE
        ]
        print(f"[Indexer] {len(supported_files)} files are supported and under size limit")

        # Step 3: Skip files already indexed (incremental update)
        already_indexed = get_indexed_file_ids(user_id)
        files_to_index = [
            f for f in supported_files
            if f["id"] not in already_indexed
        ]
        print(f"[Indexer] {len(files_to_index)} new files to index")

        # Update progress
        indexing_progress[user_id] = {
            "status": "indexing",
            "total": len(files_to_index),
            "done": 0,
            "percent": 0
        }

        if len(files_to_index) == 0:
            indexing_progress[user_id]["status"] = "complete"
            return

        # Step 4: Download and index each file
        for i, file in enumerate(files_to_index):
            try:
                file_id = file["id"]
                file_name = file.get("name", "unknown")
                extension = get_extension(file_name)
                onedrive_url = file.get("webUrl", "")
                file_path = get_file_path(file)

                print(f"[Indexer] ({i+1}/{len(files_to_index)}) Indexing: {file_name}")

                # Download the file content
                file_bytes = await download_file(access_token, file_id)
                if not file_bytes:
                    print(f"[Indexer] Skipping {file_name} — download failed")
                    continue

                # Extract text from file
                text = extract_text(file_bytes, extension)
                if not text.strip():
                    print(f"[Indexer] Skipping {file_name} — no text extracted")
                    continue

                # Store in SQLite
                upsert_file(
                    user_id=user_id,
                    file_id=file_id,
                    name=file_name,
                    path=file_path,
                    file_type=extension.lstrip("."),
                    onedrive_url=onedrive_url,
                    content=text
                )

            except Exception as e:
                print(f"[Indexer] Error indexing {file.get('name')}: {e}")

            finally:
                # Update progress after each file
                done = i + 1
                total = len(files_to_index)
                indexing_progress[user_id] = {
                    "status": "indexing",
                    "total": total,
                    "done": done,
                    "percent": round((done / total) * 100)
                }

        indexing_progress[user_id]["status"] = "complete"
        print(f"[Indexer] Indexing complete for user {user_id}")

    except Exception as e:
        print(f"[Indexer] Fatal error for user {user_id}: {e}")
        indexing_progress[user_id]["status"] = "error"


async def fetch_all_files(access_token: str) -> list:
    """
    Fetches all files from the user's OneDrive recursively.
    Walks through every folder using /children endpoint.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    files = []

    async def fetch_folder(folder_url: str):
        async with httpx.AsyncClient() as client:
            while folder_url:
                response = await client.get(folder_url, headers=headers)
                if response.status_code != 200:
                    print(f"[Indexer] Graph API error: {response.status_code} {response.text[:200]}")
                    break

                data = response.json()
                items = data.get("value", [])

                for item in items:
                    if "file" in item:
                        # It's a file — add it
                        files.append(item)
                    elif "folder" in item:
                        # It's a folder — recurse into it
                        folder_id = item["id"]
                        child_url = (
                            f"https://graph.microsoft.com/v1.0/me/drive/items/"
                            f"{folder_id}/children"
                            f"?$select=id,name,size,webUrl,parentReference,file,folder"
                            f"&$top=200"
                        )
                        await fetch_folder(child_url)

                # Handle pagination
                folder_url = data.get("@odata.nextLink", None)

    # Start from OneDrive root
    root_url = (
        "https://graph.microsoft.com/v1.0/me/drive/root/children"
        "?$select=id,name,size,webUrl,parentReference,file,folder"
        "&$top=200"
    )
    await fetch_folder(root_url)
    return files


async def download_file(access_token: str, file_id: str) -> bytes:
    """
    Downloads a file's content from OneDrive by file ID.
    Returns raw bytes or None if download fails.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print(f"[Indexer] Failed to download file {file_id}: {response.status_code}")
            return None


def get_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower()


def get_file_path(file: dict) -> str:
    """Extract the folder path from the file's parentReference."""
    parent = file.get("parentReference", {})
    return parent.get("path", "").replace("/drive/root:", "") or "/"