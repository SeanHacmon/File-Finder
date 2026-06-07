function LoginPage() {
  const handleLogin = () => {
    window.location.href = "https://file-finder-lp0y.onrender.com/auth/login";
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logo}>📁</div>
        <h1 style={styles.title}>FileFinder</h1>
        <p style={styles.subtitle}>Search inside your OneDrive files instantly</p>
        <button style={styles.button} onClick={handleLogin}>
          <svg width="20" height="20" viewBox="0 0 23 23" fill="none" style={{ marginRight: 10 }}>
            <path d="M1 1h10v10H1z" fill="#f35325"/>
            <path d="M12 1h10v10H12z" fill="#81bc06"/>
            <path d="M1 12h10v10H1z" fill="#05a6f0"/>
            <path d="M12 12h10v10H12z" fill="#ffba08"/>
          </svg>
          Sign in with Microsoft
        </button>
        <p style={styles.hint}>Works with personal and work Microsoft accounts</p>
      </div>
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    minHeight: "100vh",
    backgroundColor: "#f3f4f6",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  card: {
    backgroundColor: "white",
    borderRadius: 16,
    padding: "48px 40px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    textAlign: "center",
    maxWidth: 400,
    width: "100%",
  },
  logo: { fontSize: 48, marginBottom: 16 },
  title: { fontSize: 32, fontWeight: 700, color: "#111827", margin: "0 0 8px 0" },
  subtitle: { fontSize: 16, color: "#6b7280", margin: "0 0 32px 0", lineHeight: 1.5 },
  button: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    padding: "14px 24px",
    backgroundColor: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: 8,
    fontSize: 16,
    fontWeight: 600,
    cursor: "pointer",
    marginBottom: 16,
  },
  hint: { fontSize: 13, color: "#9ca3af", margin: 0 },
};

export default LoginPage;