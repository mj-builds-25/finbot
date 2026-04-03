"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, DemoUser } from "@/lib/api";
import { User } from "@/lib/types";
import { Loader2, Shield } from "lucide-react";

const ROLE_CONFIG: Record<string, { color: string; label: string }> = {
  employee:    { color: "#94a3b8", label: "Employee" },
  finance:     { color: "#34d399", label: "Finance" },
  engineering: { color: "#60a5fa", label: "Engineering" },
  marketing:   { color: "#a78bfa", label: "Marketing" },
  c_level:     { color: "#fbbf24", label: "C-Level" },
};

export default function LoginPage() {
  const router = useRouter();
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);
  const [loadingUser, setLoadingUser] = useState<string | null>(null);
  const [hoveredUser, setHoveredUser] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    authApi.getDemoUsers().then(setDemoUsers).catch(console.error);
    localStorage.removeItem("finbot_token");
    localStorage.removeItem("finbot_user");
  }, []);

  const handleLogin = async (user: DemoUser) => {
    setLoadingUser(user.email);
    setError("");
    try {
      const res = await authApi.login(user.email, "demo123");
      localStorage.setItem("finbot_token", res.token);
      localStorage.setItem("finbot_user", JSON.stringify({
        email: res.email, name: res.name, role: res.role,
        department: res.department, collections: res.collections,
        token: res.token,
      } as User));
      router.push("/chat");
    } catch {
      setError("Login failed. Make sure the backend is running.");
    } finally {
      setLoadingUser(null);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f0ede8",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px",
      position: "relative",
      overflow: "hidden",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>

      {/* Blobs */}
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
        <defs><filter id="b"><feGaussianBlur stdDeviation="45"/></filter></defs>
        <ellipse cx="12%" cy="18%" rx="260" ry="200" fill="#d4e4f7" opacity="0.6" filter="url(#b)"/>
        <ellipse cx="88%" cy="78%" rx="300" ry="220" fill="#e2d9f3" opacity="0.55" filter="url(#b)"/>
        <ellipse cx="80%" cy="12%" rx="180" ry="160" fill="#d4f0e4" opacity="0.5" filter="url(#b)"/>
        <ellipse cx="18%" cy="88%" rx="220" ry="170" fill="#fde8d4" opacity="0.45" filter="url(#b)"/>
      </svg>

      <div style={{ position: "relative", zIndex: 10, width: "100%", maxWidth: "420px" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            width: "56px", height: "56px", borderRadius: "16px", marginBottom: "16px",
            background: "#f0ede8",
            boxShadow: "6px 6px 14px #d4d0cb, -6px -6px 14px #ffffff",
          }}>
            {/* Neon green logo */}
            <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M12 2L3 7v6c0 5.25 3.75 10.15 9 11.25C17.25 23.15 21 18.25 21 13V7L12 2z"
                fill="#39ff14"
                stroke="#1a7a0a"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h1 className="finbot-title" style={{
  fontSize: "26px", fontWeight: 700,
  letterSpacing: "-0.5px",
}}>
  FinBot
</h1>
          <p style={{ fontSize: "13px", color: "#9ca3af", marginTop: "4px" }}>
            Internal Knowledge Assistant · FinSolve Technologies
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: "#f0ede8",
          boxShadow: "8px 8px 20px #d4d0cb, -8px -8px 20px #ffffff",
          borderRadius: "24px",
          padding: "28px",
        }}>
          <p style={{
            fontSize: "11px", fontWeight: 600, color: "#9ca3af",
            letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: "20px",
          }}>
            Select Account
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {demoUsers.map((user) => {
              const cfg = ROLE_CONFIG[user.role];
              const isLoading = loadingUser === user.email;
              const isHovered = hoveredUser === user.email;

              return (
                <button
                  key={user.email}
                  onClick={() => handleLogin(user)}
                  onMouseEnter={() => setHoveredUser(user.email)}
                  onMouseLeave={() => setHoveredUser(null)}
                  disabled={!!loadingUser}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "14px 16px",
                    borderRadius: "14px",
                    border: isHovered
                      ? `1.5px solid ${cfg.color}`
                      : "1.5px solid transparent",
                    background: "#f0ede8",
                    boxShadow: isHovered
                      ? `3px 3px 8px #d4d0cb, -3px -3px 8px #ffffff, 0 0 14px ${cfg.color}33`
                      : "4px 4px 10px #d4d0cb, -4px -4px 10px #ffffff",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    opacity: loadingUser && !isLoading ? 0.5 : 1,
                  }}
                >
                  {/* Left: avatar + name */}
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                      width: "38px", height: "38px", borderRadius: "10px", flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "12px", fontWeight: 600, color: "#6b7280",
                      background: "#f0ede8",
                      boxShadow: "inset 3px 3px 7px #d4d0cb, inset -3px -3px 7px #ffffff",
                    }}>
                      {user.name.split(" ").map((n: string) => n[0]).join("")}
                    </div>
                    <div style={{ textAlign: "left" }}>
                      <p style={{
                        fontSize: "14px", fontWeight: 600,
                        color: "#374151",
                        letterSpacing: "-0.2px",
                      }}>
                        {user.name}
                      </p>
                      <p style={{ fontSize: "12px", color: "#9ca3af" }}>
                        {user.department}
                      </p>
                    </div>
                  </div>

                  {/* Right: role badge + loader */}
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{
                      display: "flex", alignItems: "center", gap: "6px",
                      fontSize: "12px", fontWeight: 500,
                      color: cfg.color,
                    }}>
                      <span style={{
                        width: "6px", height: "6px", borderRadius: "50%",
                        background: cfg.color,
                        flexShrink: 0,
                      }}/>
                      {cfg.label}
                    </span>
                    {isLoading && (
                      <Loader2 size={14} color="#9ca3af"/>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {error && (
            <div style={{
              marginTop: "16px", padding: "12px", borderRadius: "10px",
              background: "#f0ede8",
              boxShadow: "inset 3px 3px 7px #d4d0cb, inset -3px -3px 7px #ffffff",
              fontSize: "12px", color: "#f87171",
            }}>
              {error}
            </div>
          )}

          <p style={{
            textAlign: "center", fontSize: "12px",
            color: "#9ca3af", marginTop: "20px",
          }}>
            All accounts · password:{" "}
            <span style={{ fontFamily: "monospace", color: "#6b7280" }}>demo123</span>
          </p>
        </div>
      </div>
      <style>{`
  @keyframes gradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  .finbot-title {
    background: linear-gradient(
      270deg,
      #34d399,
      #60a5fa,
      #a78bfa,
      #fbbf24,
      #34d399
    );
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientFlow 6s ease infinite;
  }
`}</style>
    </div>
  );
}