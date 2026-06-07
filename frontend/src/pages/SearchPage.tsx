import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API = "https://file-finder-lp0y.onrender.com";

interface SearchResult {
  id: string;
  name: string;
  path: string;
  file_type: string;
  snippet: string;
  score: number;
  onedrive_url: string;
}

interface User {
  id: string;
  name: string;
  email: string;
  token: string;
}

interface Progress {
  status: string;
  total: number;
  done: number;
  percent: number;
}

function getHeaders(user: User) {
  return {
    Authorization: `Bearer ${user.token}`,
    "X-User-Id": user.id,
    "X-User-Name": user.name,
    "X-User-Email": user.email,
  };
}

function SearchPage() {
  const [user, setUser] = useState<User | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const uid = params.get("uid");
    const name = params.get("name");
    const email = params.get("email");
    const token = params.get("token");

    if (uid && email && token) {
      const userData: User = { id: uid, name: name || "", email: email || "", token };
      setUser(userData);
      localStorage.setItem("filefinder_user", JSON.stringify(userData));
      window.history.replaceState({}, "", "/search");
      return;
    }

    const stored = localStorage.getItem("filefinder_user");
    if (stored) {
      try {
        setUser(JSON.parse(stored));
        return;
      } catch {
        localStorage.removeItem("filefinder_user");
      }
    }

    window.location.href = "/";
  }, []);

  useEffect(() => {
    if (!user) return;
    axios.post(`${API}/index`, {}, { withCredentials: true, headers: getHeaders(user) })
      .catch((err) => console.log("Index trigger:", err));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/index/progress`, {
          withCredentials: true,
          headers: getHeaders(user),
        });
        setProgress(res.data);
        if (res.data.status === "complete" || res.data.status === "error") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [user]);

  const handleSearch = useCallback(async () => {
    if (!query.trim() || !user) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await axios.get(`${API}/search`, {
        params: { q: query, limit: 20 },
        withCredentials: true,
        headers: getHeaders(user),
      });
      setResults(res.data.results || []);
    } catch (err) {
      console.error("Search error:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, user]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleLogout = async () => {
    if (user) {
      await axios.post(`${API}/auth/logout`, {}, {
        withCredentials: true,
        headers: getHeaders(user)
      }).catch(() => {});
    }
    localStorage.removeItem("filefinder_user");
    window.location.href = "/";
  };

  const getFileIcon = (type: string) => {
    const icons: { [key: string]: string } = {
      pdf: "📄", docx: "📝", xlsx: "📊", txt: "📃",
    };
    return icons[type] || "📁";
  };

  const showProgress =
    progress &&
    progress.status !== "not_started" &&
    progress.status !== "complete";

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerLogo}>📁</span>
          <span style={styles.headerTitle}>FileFinder</span>
        </div>
        {user && (
          <div style={styles.headerRight}>
            <span style={styles.userEmail}>{user.email}</span>
            <button style={styles.logoutBtn} onClick={handleLogout}>Sign out</button>
          </div>
        )}
      </div>

      <div style={styles.main}>
        {showProgress && (
          <div style={styles.progressBanner}>
            <div style={styles.progressText}>
              {progress.status === "fetching"
                ? "📂 Fetching your OneDrive files..."
                : `⚙️ Indexing your files... ${progress.percent}% (${progress.done}/${progress.total})`}
            </div>
            <div style={styles.progressBarBg}>
              <div style={{ ...styles.progressBarFill, width: `${progress.percent}%` }} />
            </div>
            <p style={styles.progressHint}>You can search while indexing continues in the background</p>
          </div>
        )}

        {progress?.status === "complete" && !searched && (
          <div style={styles.successBanner}>✅ All files indexed — search is ready!</div>
        )}

        <div style={styles.searchSection}>
          {!searched && <h2 style={styles.searchTitle}>Search inside your files</h2>}
          <div style={styles.searchBar}>
            <input
              style={styles.searchInput}
              type="text"
              placeholder='Try "gary beer" or "budget Q3" or "meeting notes"'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
            <button style={styles.searchButton} onClick={handleSearch} disabled={loading}>
              {loading ? "..." : "Search"}
            </button>
          </div>
        </div>

        {searched && !loading && (
          <div style={styles.results}>
            {results.length === 0 ? (
              <div style={styles.noResults}>
                <p style={{ fontSize: 32 }}>🔍</p>
                <p style={{ color: "#6b7280", fontSize: 16 }}>No files found for <strong>"{query}"</strong></p>
                <p style={{ color: "#9ca3af", fontSize: 14 }}>Try different keywords or wait for indexing to complete</p>
              </div>
            ) : (
              <>
                <p style={styles.resultCount}>
                  {results.length} file{results.length !== 1 ? "s" : ""} found for <strong>"{query}"</strong>
                </p>
                {results.map((result) => (
                  <a key={result.id} href={result.onedrive_url} target="_blank" rel="noopener noreferrer" style={styles.resultCard}>
                    <div style={styles.resultHeader}>
                      <span style={styles.fileIcon}>{getFileIcon(result.file_type)}</span>
                      <div style={styles.resultMeta}>
                        <span style={styles.fileName}>{result.name}</span>
                        <span style={styles.filePath}>{result.path}</span>
                      </div>
                      <span style={styles.fileType}>{result.file_type.toUpperCase()}</span>
                    </div>
                    {result.snippet && (
                      <p style={styles.snippet} dangerouslySetInnerHTML={{
                        __html: result.snippet.replace(/\[([^\]]+)\]/g, '<mark style="background:#fef08a;padding:0 2px;border-radius:2px">$1</mark>')
                      }} />
                    )}
                  </a>
                ))}
              </>
            )}
          </div>
        )}

        {!searched && (
          <div style={styles.emptyState}>
            <p>🔍 Type keywords to search inside your OneDrive files</p>
            <p style={{ fontSize: 14, color: "#9ca3af" }}>Searches inside .txt, .pdf, .docx, and .xlsx files</p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: { minHeight: "100vh", backgroundColor: "#f9fafb", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" },
  header: { backgroundColor: "white", borderBottom: "1px solid #e5e7eb", padding: "0 24px", height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky" as const, top: 0, zIndex: 100 },
  headerLeft: { display: "flex", alignItems: "center", gap: 8 },
  headerLogo: { fontSize: 24 },
  headerTitle: { fontSize: 20, fontWeight: 700, color: "#111827" },
  headerRight: { display: "flex", alignItems: "center", gap: 16 },
  userEmail: { fontSize: 14, color: "#6b7280" },
  logoutBtn: { padding: "6px 14px", backgroundColor: "transparent", border: "1px solid #e5e7eb", borderRadius: 6, fontSize: 14, color: "#374151", cursor: "pointer" },
  main: { maxWidth: 720, margin: "0 auto", padding: "40px 24px" },
  progressBanner: { backgroundColor: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "16px 20px", marginBottom: 24 },
  progressText: { fontSize: 14, fontWeight: 600, color: "#1d4ed8", marginBottom: 8 },
  progressBarBg: { backgroundColor: "#dbeafe", borderRadius: 99, height: 6, overflow: "hidden" },
  progressBarFill: { backgroundColor: "#2563eb", height: "100%", borderRadius: 99, transition: "width 0.5s ease" },
  progressHint: { fontSize: 12, color: "#6b7280", margin: "8px 0 0 0" },
  successBanner: { backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "12px 20px", marginBottom: 24, fontSize: 14, color: "#15803d", fontWeight: 600 },
  searchSection: { marginBottom: 32 },
  searchTitle: { fontSize: 28, fontWeight: 700, color: "#111827", margin: "0 0 20px 0", textAlign: "center" as const },
  searchBar: { display: "flex", gap: 8 },
  searchInput: { flex: 1, padding: "14px 18px", fontSize: 16, border: "1px solid #e5e7eb", borderRadius: 10, outline: "none", backgroundColor: "white", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" },
  searchButton: { padding: "14px 24px", backgroundColor: "#2563eb", color: "white", border: "none", borderRadius: 10, fontSize: 16, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" as const },
  results: { display: "flex", flexDirection: "column" as const, gap: 12 },
  resultCount: { fontSize: 14, color: "#6b7280", margin: "0 0 8px 0" },
  resultCard: { backgroundColor: "white", border: "1px solid #e5e7eb", borderRadius: 10, padding: "16px 20px", textDecoration: "none", color: "inherit", display: "block", cursor: "pointer" },
  resultHeader: { display: "flex", alignItems: "center", gap: 12, marginBottom: 8 },
  fileIcon: { fontSize: 24 },
  resultMeta: { flex: 1, display: "flex", flexDirection: "column" as const, gap: 2 },
  fileName: { fontSize: 16, fontWeight: 600, color: "#111827" },
  filePath: { fontSize: 12, color: "#9ca3af" },
  fileType: { fontSize: 11, fontWeight: 700, color: "#6b7280", backgroundColor: "#f3f4f6", padding: "2px 8px", borderRadius: 4 },
  snippet: { fontSize: 14, color: "#4b5563", margin: 0, lineHeight: 1.6, borderTop: "1px solid #f3f4f6", paddingTop: 8 },
  noResults: { textAlign: "center" as const, padding: "48px 0" },
  emptyState: { textAlign: "center" as const, color: "#6b7280", fontSize: 16, marginTop: 48, lineHeight: 2 },
};

export default SearchPage;