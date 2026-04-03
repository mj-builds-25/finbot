"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { chatApi, ChatResponse } from "@/lib/api";
import { User, Message, ROLE_LABELS } from "@/lib/types";
import {
  Send, LogOut, AlertTriangle, FileText,
  ChevronDown, ChevronUp, Loader2, Info, Shield,
} from "lucide-react";

const ROLE_THEME: Record<string, {
  dot: string;
  cardBg: string;
  cardBorder: string;
  avatarBg: string;
  badgeBg: string;
  badgeBorder: string;
  bubbleBg: string;
  bubbleText: string;
  nameText: string;
  subText: string;
}> = {
  employee: {
    dot:         "#94a3b8",
    cardBg:      "rgba(148,163,184,0.12)",
    cardBorder:  "rgba(148,163,184,0.3)",
    avatarBg:    "rgba(148,163,184,0.35)",
    badgeBg:     "rgba(148,163,184,0.25)",
    badgeBorder: "rgba(148,163,184,0.4)",
    bubbleBg:    "#dde3ec",
    bubbleText:  "#1e293b",
    nameText:    "#1e293b",
    subText:     "#475569",
  },
  finance: {
    dot:         "#34d399",
    cardBg:      "rgba(52,211,153,0.12)",
    cardBorder:  "rgba(52,211,153,0.3)",
    avatarBg:    "rgba(52,211,153,0.35)",
    badgeBg:     "rgba(52,211,153,0.25)",
    badgeBorder: "rgba(52,211,153,0.4)",
    bubbleBg:    "#c6f0e0",
    bubbleText:  "#064e35",
    nameText:    "#064e35",
    subText:     "#1a6b4a",
  },
  engineering: {
    dot:         "#60a5fa",
    cardBg:      "rgba(96,165,250,0.12)",
    cardBorder:  "rgba(96,165,250,0.3)",
    avatarBg:    "rgba(96,165,250,0.35)",
    badgeBg:     "rgba(96,165,250,0.25)",
    badgeBorder: "rgba(96,165,250,0.4)",
    bubbleBg:    "#cce0fd",
    bubbleText:  "#1e3a5f",
    nameText:    "#1e3a5f",
    subText:     "#2d5a8e",
  },
  marketing: {
    dot:         "#a78bfa",
    cardBg:      "rgba(167,139,250,0.12)",
    cardBorder:  "rgba(167,139,250,0.3)",
    avatarBg:    "rgba(167,139,250,0.35)",
    badgeBg:     "rgba(167,139,250,0.25)",
    badgeBorder: "rgba(167,139,250,0.4)",
    bubbleBg:    "#e4dcfd",
    bubbleText:  "#2e1a5f",
    nameText:    "#2e1a5f",
    subText:     "#5b3fa8",
  },
  c_level: {
    dot:         "#fbbf24",
    cardBg:      "rgba(251,191,36,0.12)",
    cardBorder:  "rgba(251,191,36,0.3)",
    avatarBg:    "rgba(251,191,36,0.35)",
    badgeBg:     "rgba(251,191,36,0.25)",
    badgeBorder: "rgba(251,191,36,0.4)",
    bubbleBg:    "#fdefc9",
    bubbleText:  "#5f3a00",
    nameText:    "#5f3a00",
    subText:     "#92580a",
  },
};

const neu = {
  card: {
    background: "#f0ede8",
    boxShadow: "8px 8px 20px #d4d0cb, -8px -8px 20px #ffffff",
    borderRadius: "20px",
  } as React.CSSProperties,
  inset: {
    background: "#f0ede8",
    boxShadow: "inset 3px 3px 8px #d4d0cb, inset -3px -3px 8px #ffffff",
    borderRadius: "12px",
  } as React.CSSProperties,
};

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2));
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [logoutHover, setLogoutHover] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored) as User;
    setUser(u);
    setMessages([{
      id: "welcome", role: "assistant",
      content: `Hi ${u.name.split(" ")[0]}! I'm FinBot. You have access to: ${u.collections.join(", ")} documents. What would you like to know?`,
      timestamp: new Date(),
    }]);
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLogout = () => {
    localStorage.removeItem("finbot_token");
    localStorage.removeItem("finbot_user");
    router.push("/");
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = {
      id: Date.now().toString(), role: "user",
      content: input.trim(), timestamp: new Date(),
    };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res: ChatResponse = await chatApi.sendMessage(input.trim(), sessionId);
      setMessages((p) => [...p, {
        id: (Date.now() + 1).toString(), role: "assistant",
        content: res.answer, sources: res.sources,
        route: res.route, route_score: res.route_score,
        collections_searched: res.collections_searched,
        chunks_retrieved: res.chunks_retrieved,
        input_blocked: res.input_blocked,
        output_warnings: res.output_warnings,
        allowed: res.allowed, timestamp: new Date(),
      }]);
    } catch {
      setMessages((p) => [...p, {
        id: (Date.now() + 1).toString(), role: "assistant",
        content: "Something went wrong. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (id: string) => {
    setExpandedSources((p) => {
      const n = new Set(p);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  if (!user) return null;

  const font = { fontFamily: "'Inter', system-ui, sans-serif" };

  return (
    <div style={{
      display: "flex", height: "100vh",
      background: "#f0ede8",
      position: "relative", overflow: "hidden", ...font,
    }}>

      {/* Blobs */}
      <svg style={{
        position: "absolute", inset: 0,
        width: "100%", height: "100%",
        pointerEvents: "none", zIndex: 0,
      }}>
        <defs><filter id="b2"><feGaussianBlur stdDeviation="50"/></filter></defs>
        <ellipse cx="90%" cy="8%"  rx="280" ry="220" fill="#d4e4f7" opacity="0.45" filter="url(#b2)"/>
        <ellipse cx="5%"  cy="92%" rx="260" ry="200" fill="#e2d9f3" opacity="0.4"  filter="url(#b2)"/>
        <ellipse cx="50%" cy="50%" rx="200" ry="160" fill="#d4f0e4" opacity="0.2"  filter="url(#b2)"/>
      </svg>

      {/* Sidebar */}
      <div style={{
        position: "relative", zIndex: 10,
        width: "220px", flexShrink: 0,
        padding: "16px",
        display: "flex", flexDirection: "column", gap: "12px",
      }}>

        {/* Logo */}
        <div style={{ ...neu.card, padding: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            ...neu.inset,
            width: "32px", height: "32px", borderRadius: "10px",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            {/* Neon green logo */}
            {/* <Shield size={16} color="#39ff14"/> */}
            <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L3 7v6c0 5.25 3.75 10.15 9 11.25C17.25 23.15 21 18.25 21 13V7L12 2z"
                  fill="#39ff14"
                  stroke="#1a7a0a"
                  strokeWidth="1.2"
                  strokeLinejoin="round"
                />
            </svg>
          </div>
          <div>
            <p style={{ fontSize: "14px", fontWeight: 700, color: "#374151", letterSpacing: "-0.3px" }}>
              FinBot
            </p>
            <p style={{ fontSize: "11px", color: "#9ca3af" }}>FinSolve AI</p>
          </div>
        </div>
        {/* User card — role-colored */}
{(() => {
  const t = ROLE_THEME[user.role];
  return (
    <div style={{
      background: t.cardBg,
      boxShadow: `8px 8px 20px #d4d0cb, -8px -8px 20px #ffffff, inset 0 0 0 1.5px ${t.cardBorder}`,
      borderRadius: "20px",
      padding: "16px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
        <div style={{
          width: "34px", height: "34px", borderRadius: "10px", flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "11px", fontWeight: 700, color: "#ffffff",
          background: t.avatarBg,
          boxShadow: "inset 2px 2px 5px rgba(0,0,0,0.08)",
        }}>
          {user.name.split(" ").map((n) => n[0]).join("")}
        </div>
        <div>
          <p style={{ fontSize: "13px", fontWeight: 700, color: t.nameText }}>{user.name}</p>
          <p style={{ fontSize: "11px", color: t.subText }}>{user.department}</p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "12px" }}>
        <span style={{
          width: "6px", height: "6px", borderRadius: "50%",
          background: t.dot, flexShrink: 0,
        }}/>
        <span style={{ fontSize: "12px", color: t.nameText, fontWeight: 600 }}>
          {ROLE_LABELS[user.role]}
        </span>
      </div>

      <div>
        <p style={{
          fontSize: "10px", fontWeight: 600, color: t.subText,
          letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "8px",
        }}>
          Access
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {user.collections.map((c) => (
            <span key={c} style={{
              padding: "3px 8px",
              fontSize: "11px", fontWeight: 600,
              color: t.nameText,
              background: t.badgeBg,
              borderRadius: "8px",
              boxShadow: `inset 0 0 0 1px ${t.badgeBorder}`,
            }}>
              {c}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
})()}

        
        
      </div>

      {/* Main chat area */}
      <div style={{
        position: "relative", zIndex: 10,
        flex: 1, display: "flex", flexDirection: "column",
        padding: "16px 16px 16px 0", minWidth: 0,
      }}>
        <div style={{ ...neu.card, flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {/* Header — sign out top right */}
          <div style={{
            padding: "16px 24px",
            borderBottom: "1px solid #e0dcd6",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <div>
              <p style={{ fontSize: "14px", fontWeight: 600, color: "#374151" }}>Chat</p>
              <p style={{ fontSize: "12px", color: "#9ca3af" }}>
                Ask questions about your authorized documents
              </p>
            </div>

            {/* Sign out — solid neon on hover */}
            <button
              onClick={handleLogout}
              onMouseEnter={() => setLogoutHover(true)}
              onMouseLeave={() => setLogoutHover(false)}
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                padding: "8px 16px", borderRadius: "10px",
                border: "none", cursor: "pointer",
                fontSize: "13px", fontWeight: 600,
                color: logoutHover ? "#0f0f0f" : "#6b7280",
                background: logoutHover ? "#39ff14" : "#f0ede8",
                boxShadow: logoutHover
                  ? "0 0 18px rgba(57,255,20,0.45), 4px 4px 10px #d4d0cb"
                  : "4px 4px 10px #d4d0cb, -4px -4px 10px #ffffff",
                outline: "none",
                transition: "all 0.15s ease",
              }}
            >
              <LogOut size={14}/>
              Sign out
            </button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto",
            padding: "20px 24px",
            display: "flex", flexDirection: "column", gap: "16px",
          }}>
            {messages.map((msg) => (
              <div key={msg.id} style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              }}>
                <div style={{ maxWidth: "640px", width: "100%" }}>

                  {/* Guardrail banner */}
                  {msg.input_blocked && (
                    <div style={{
                      display: "flex", alignItems: "flex-start", gap: "8px",
                      marginBottom: "8px", ...neu.inset, padding: "10px 12px",
                    }}>
                      <AlertTriangle size={14} color="#f87171" style={{ marginTop: "1px", flexShrink: 0 }}/>
                      <p style={{ fontSize: "12px", color: "#f87171" }}>
                        Guardrail triggered — query blocked before processing.
                      </p>
                    </div>
                  )}

                  {/* Output warnings */}
                  {msg.output_warnings && msg.output_warnings.length > 0 && (
                    <div style={{
                      display: "flex", alignItems: "flex-start", gap: "8px",
                      marginBottom: "8px", ...neu.inset, padding: "10px 12px",
                    }}>
                      <AlertTriangle size={14} color="#f59e0b" style={{ marginTop: "1px", flexShrink: 0 }}/>
                      <p style={{ fontSize: "12px", color: "#f59e0b" }}>
                        {msg.output_warnings[0]}
                      </p>
                    </div>
                  )}

                  {/* Message bubble */}
                  <div style={{
  ...neu.inset,
  padding: "12px 16px",
  borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
  background: msg.role === "user"
    ? ROLE_THEME[user.role].cardBg
    : "#f0ede8",
  boxShadow: msg.role === "user"
    ? `inset 3px 3px 8px rgba(0,0,0,0.06), inset -3px -3px 8px #ffffff, inset 0 0 0 1.5px ${ROLE_THEME[user.role].cardBorder}`
    : "inset 3px 3px 8px #d4d0cb, inset -3px -3px 8px #ffffff",
}}>
  <p style={{
    fontSize: "14px", lineHeight: "1.6",
    whiteSpace: "pre-wrap",
    color: msg.role === "user"
      ? ROLE_THEME[user.role].nameText
      : "#374151",
  }}>
    {msg.content}
  </p>
</div>

                  {/* Route metadata */}
                  {msg.role === "assistant" && msg.route && (
                    <div style={{
                      display: "flex", alignItems: "center", gap: "12px",
                      marginTop: "6px", paddingLeft: "4px",
                    }}>
                      <span style={{
                        display: "flex", alignItems: "center", gap: "4px",
                        fontSize: "11px", color: "#9ca3af",
                      }}>
                        <Info size={11}/>
                        {msg.route.replace("_route", "")} · {(msg.route_score! * 100).toFixed(0)}%
                      </span>
                      {msg.chunks_retrieved !== undefined && msg.chunks_retrieved > 0 && (
                        <span style={{ fontSize: "11px", color: "#9ca3af" }}>
                          {msg.chunks_retrieved} chunks
                        </span>
                      )}
                    </div>
                  )}

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: "8px", paddingLeft: "4px" }}>
                      <button
                        onClick={() => toggleSources(msg.id)}
                        style={{
                          display: "flex", alignItems: "center", gap: "6px",
                          fontSize: "12px", color: "#6b7280",
                          background: "none", border: "none",
                          cursor: "pointer", padding: 0,
                        }}
                      >
                        <FileText size={12}/>
                        {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                        {expandedSources.has(msg.id)
                          ? <ChevronUp size={12}/>
                          : <ChevronDown size={12}/>
                        }
                      </button>

                      {expandedSources.has(msg.id) && (
                        <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "6px" }}>
                          {msg.sources.map((src, i) => (
                            <div key={i} style={{
                              ...neu.inset,
                              padding: "10px 12px",
                              display: "flex", alignItems: "flex-start", gap: "8px",
                            }}>
                              <FileText size={12} color="#9ca3af" style={{ marginTop: "2px", flexShrink: 0 }}/>
                              <div>
                                <p style={{ fontSize: "12px", fontWeight: 600, color: "#374151" }}>
                                  {src.document}
                                </p>
                                <p style={{ fontSize: "11px", color: "#9ca3af" }}>
                                  {src.section} · p.{src.page} · {(src.score * 100).toFixed(0)}%
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ ...neu.inset, padding: "12px 16px", borderRadius: "16px" }}>
                  <Loader2 size={16} color="#9ca3af"/>
                </div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Input area */}
          <div style={{ padding: "16px 24px", borderTop: "1px solid #e0dcd6" }}>
            <div style={{ display: "flex", gap: "12px", alignItems: "flex-end" }}>
              <div style={{ flex: 1, ...neu.inset, padding: "12px 16px" }}>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={`Ask about ${user.collections.join(", ")}...`}
                  rows={1}
                  style={{
                    width: "100%", background: "transparent",
                    border: "none", outline: "none", resize: "none",
                    fontSize: "14px", color: "#374151",
                    fontFamily: "'Inter', system-ui, sans-serif",
                    minHeight: "22px", maxHeight: "100px",
                  }}
                />
              </div>

              {/* Send — role-colored */}
<button
  onClick={handleSend}
  disabled={!input.trim() || loading}
  style={{
    width: "42px", height: "42px", flexShrink: 0,
    display: "flex", alignItems: "center", justifyContent: "center",
    borderRadius: "12px", border: "none",
    cursor: input.trim() && !loading ? "pointer" : "not-allowed",
    opacity: !input.trim() || loading ? 0.4 : 1,
    background: ROLE_THEME[user.role].dot,
    boxShadow: `0 0 14px ${ROLE_THEME[user.role].dot}66, 4px 4px 10px #d4d0cb`,
    transition: "all 0.15s ease",
  }}
>
  <Send size={16} color="#ffffff"/>
</button>
            </div>

            <p style={{
              textAlign: "center", fontSize: "11px",
              color: "#9ca3af", marginTop: "8px",
            }}>
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}