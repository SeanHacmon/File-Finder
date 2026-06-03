# 📁 FileFinder

A web application that lets users sign in with their Microsoft account and search for files in their OneDrive — not just by filename, but by **keywords found inside the file content**.

**Example:** You have a file called `data.txt` containing _"hello my name is gary and i like beer"_ but you don't remember the filename. Search `gary beer` and FileFinder finds it instantly.

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript |
| Backend | FastAPI (Python 3.11+) |
| Auth | Microsoft OAuth 2.0 (MSAL) |
| File Access | Microsoft Graph API v1.0 |
| Search Engine | SQLite FTS5 (built-in, free) |
| Text Extraction | pypdf, python-docx, openpyxl |
| Hosting (Frontend) | Vercel (free) |
| Hosting (Backend) | Render (free / $7/month always-on) |

---

## 📂 Project Structure

```
FileFinder/
└── onedrive-search/
    ├── backend/
    │   ├── main.py           # FastAPI server + all endpoints
    │   ├── auth.py           # Microsoft OAuth login flow
    │   ├── database.py       # SQLite FTS5 setup + search queries
    │   ├── extractor.py      # Text extraction (PDF, DOCX, XLSX, TXT)
    │   ├── indexer.py        # Smart background OneDrive file indexer
    │   ├── requirements.txt  # Python dependencies
    │   └── .env              # ⚠️ NOT in GitHub — see setup below
    │
    └── frontend/
        └── src/
            ├── App.tsx
            └── pages/
                ├── LoginPage.tsx
                └── SearchPage.tsx
```

---

## ⚠️ Files NOT Included in This Repo

These files are excluded from GitHub for security reasons. You must create them manually:

### 1. `backend/.env`
Create this file in the `backend/` folder with your Azure credentials:

```
CLIENT_ID=your_azure_client_id
CLIENT_SECRET=your_azure_client_secret
TENANT_ID=common
REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=any_random_string_you_make_up
```

To get `CLIENT_ID`, `CLIENT_SECRET`:
- Go to [portal.azure.com](https://portal.azure.com)
- Find the **FileFinder** app registration
- Copy **Application (client) ID** → `CLIENT_ID`
- Go to **Certificates & secrets** → copy your secret value → `CLIENT_SECRET`
- Leave `TENANT_ID` as `common` to support all Microsoft account types

### 2. `backend/filefinder.db`
This is the SQLite database. It is auto-created when you run the backend for the first time. No action needed — just run the server and it appears automatically.

---

## 🚀 Running Locally (New Machine Setup)

### Prerequisites
Make sure you have installed:
- Python 3.11+
- Node.js 18+
- npm

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME/onedrive-search
```

### Step 2 — Backend setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Mac/Linux
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

Create your `.env` file (see ⚠️ Files NOT Included section above).

Start the backend:
```bash
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

### Step 3 — Frontend setup
Open a second terminal:
```bash
cd frontend
npm install
npm start
```

Frontend runs at: `http://localhost:3000`

### Step 4 — Test it
1. Go to `http://localhost:3000`
2. Click **Sign in with Microsoft**
3. Sign in with your Microsoft / Gmail account
4. Wait for indexing to complete (progress bar shown)
5. Search for keywords inside your files

---

## 🔑 Azure App Registration

This app requires an Azure App Registration to connect to Microsoft OneDrive. The app is already registered — you just need the credentials from the existing registration.

**If you need to register a new app:**
1. Go to [portal.azure.com](https://portal.azure.com)
2. Search **App registrations** → **New registration**
3. Name: `FileFinder`
4. Supported account types: `Any Entra ID Tenant + Personal Microsoft accounts`
5. Redirect URI: `Web` → `http://localhost:8000/auth/callback`
6. After registering, go to **API permissions** → Add:
   - `Files.Read`
   - `Files.Read.All`
   - `User.Read`
   - `offline_access`

---

## 🔍 How Search Works

1. **First login** — app crawls your OneDrive and extracts text from all `.txt`, `.pdf`, `.docx`, `.xlsx` files under 10MB
2. **Text is stored** in a local SQLite database using FTS5 (full-text search)
3. **Every search** queries the SQLite index — results in under 1 second
4. **Subsequent logins** — only new or changed files are re-indexed (fast)

Supported file types: `.txt` `.pdf` `.docx` `.xlsx`

---

## 🌐 Deploying to Production

### Frontend → Vercel
1. Go to [vercel.com](https://vercel.com) → Import GitHub repo
2. Set root directory to `frontend`
3. Deploy → get URL like `https://filefinder.vercel.app`

### Backend → Render
1. Go to [render.com](https://render.com) → New Web Service → Import GitHub repo
2. Set root directory to `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Add all `.env` variables in the Render environment settings
6. Deploy → get URL like `https://filefinder-api.onrender.com`

### After deploying both:
- Update `const API` in `SearchPage.tsx` to your Render backend URL
- Update `window.location.href` in `LoginPage.tsx` to your Render backend URL
- Add the Render callback URL to Azure portal → Authentication → Redirect URIs:
  `https://filefinder-api.onrender.com/auth/callback`

---

## 📦 Backend Dependencies

All listed in `requirements.txt`. Key packages:

| Package | Purpose |
|---|---|
| fastapi | Web framework |
| uvicorn | ASGI server |
| httpx | Async HTTP client for Graph API |
| pypdf | Extract text from PDF files |
| python-docx | Extract text from Word files |
| openpyxl | Extract text from Excel files |
| python-dotenv | Load .env file |
| itsdangerous | Session encryption |

---

## 🔒 Security Notes

- Each user only sees their own files — SQLite rows are tagged by `user_id`
- Access tokens are stored server-side in sessions only
- The `.env` file is in `.gitignore` and never committed
- File content stays on your server — no third-party service receives your data

---

## 👨‍💻 Author

Sean Hacmon
