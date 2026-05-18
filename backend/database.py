import sqlite3
import os

DB_PATH = "filefinder.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Main file metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            name         TEXT NOT NULL,
            path         TEXT,
            file_type    TEXT,
            onedrive_url TEXT,
            indexed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FTS5 full-text search table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
            file_id,
            content,
            tokenize = 'porter unicode61'
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")

def upsert_file(user_id, file_id, name, path, file_type, onedrive_url, content):
    conn = get_connection()
    cursor = conn.cursor()

    # Insert or replace file metadata
    cursor.execute("""
        INSERT OR REPLACE INTO files (id, user_id, name, path, file_type, onedrive_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file_id, user_id, name, path, file_type, onedrive_url))

    # Remove old FTS entry if exists
    cursor.execute("DELETE FROM file_fts WHERE file_id = ?", (file_id,))

    # Insert new FTS entry
    cursor.execute("""
        INSERT INTO file_fts (file_id, content)
        VALUES (?, ?)
    """, (file_id, content))

    conn.commit()
    conn.close()

def search_files(user_id, query, limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            f.id,
            f.name,
            f.path,
            f.file_type,
            f.onedrive_url,
            snippet(file_fts, 1, '[', ']', '...', 20) AS snippet,
            rank
        FROM file_fts
        JOIN files f ON file_fts.file_id = f.id
        WHERE file_fts MATCH ? AND f.user_id = ?
        ORDER BY rank
        LIMIT ?
    """, (query, user_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_indexed_file_ids(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return {row["id"] for row in rows}