"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { chatApi, ChatResponse } from "@/lib/api";
import { User, Message, ROLE_COLORS, ROLE_LABELS } from "@/lib/types";
import {
  Send, LogOut, Shield, AlertTriangle,
  FileText, ChevronDown, ChevronUp, Loader2, Info
} from "lucide-react";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).slice(2));
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("finbot_user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored) as User;
    setUser(u);

    // Welcome message
    setMessages([{
      id: "welcome",
      role: "assistant",
      content: `Hello ${u.name}! I'm FinBot, your internal knowledge assistant. You're logged in as **${ROLE_LABELS[u.role]}** with access to: ${u.collections.join(", ")} documents.\n\nWhat would you like to know?`,
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
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: ChatResponse = await chatApi.sendMessage(input.trim(), sessionId);

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        route: res.route,
        route_score: res.route_score,
        collections_searched: res.collections_searched,
        chunks_retrieved: res.chunks_retrieved,
        input_blocked: res.input_blocked,
        output_warnings: res.output_warnings,
        allowed: res.allowed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  };

  if (!user) return null;

  const roleColor = ROLE_COLORS[user.role] || "bg-gray-100 text-gray-700";

  return (
    <div className="flex flex-col h-screen bg-slate-900">

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-blue-400" />
          <span className="text-white font-semibold text-lg">FinBot</span>
        </div>

        {/* Role + collections indicator */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 text-slate-400 text-sm">
            <span>Access:</span>
            {user.collections.map((c) => (
              <span key={c} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300">
                {c}
              </span>
            ))}
          </div>
          <span className={`text-xs font-medium px-3 py-1 rounded-full ${roleColor}`}>
            {user.name} · {ROLE_LABELS[user.role]}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-slate-400 hover:text-white text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-3xl w-full ${msg.role === "user" ? "ml-12" : "mr-12"}`}>

              {/* Guardrail warning banner */}
              {msg.input_blocked && (
                <div className="flex items-start gap-2 mb-2 p-3 bg-red-900/40 border border-red-700 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
                  <p className="text-red-300 text-sm">
                    <span className="font-medium">Guardrail triggered</span> — this query was blocked before processing.
                  </p>
                </div>
              )}

              {/* Output warnings */}
              {msg.output_warnings && msg.output_warnings.length > 0 && (
                <div className="flex items-start gap-2 mb-2 p-3 bg-amber-900/40 border border-amber-700 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-amber-300 text-sm">
                    <span className="font-medium">Output warning:</span> {msg.output_warnings[0]}
                  </p>
                </div>
              )}

              {/* Message bubble */}
              <div className={`rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-100 border border-slate-700"
              }`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content}
                </p>
              </div>

              {/* Metadata row (assistant messages only) */}
              {msg.role === "assistant" && msg.route && (
                <div className="mt-2 flex items-center gap-3 flex-wrap">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Info className="w-3 h-3" />
                    Route: <span className="text-slate-400">{msg.route}</span>
                    <span className="text-slate-600">({(msg.route_score! * 100).toFixed(0)}%)</span>
                  </span>
                  {msg.collections_searched && msg.collections_searched.length > 0 && (
                    <span className="text-xs text-slate-500">
                      Searched: {msg.collections_searched.join(", ")}
                    </span>
                  )}
                  {msg.chunks_retrieved !== undefined && msg.chunks_retrieved > 0 && (
                    <span className="text-xs text-slate-500">
                      {msg.chunks_retrieved} chunks
                    </span>
                  )}
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleSources(msg.id)}
                    className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    <FileText className="w-3 h-3" />
                    {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                    {expandedSources.has(msg.id)
                      ? <ChevronUp className="w-3 h-3" />
                      : <ChevronDown className="w-3 h-3" />
                    }
                  </button>

                  {expandedSources.has(msg.id) && (
                    <div className="mt-2 space-y-1.5">
                      {msg.sources.map((src, i) => (
                        <div key={i} className="flex items-start gap-2 p-2.5 bg-slate-700/50 rounded-lg border border-slate-700">
                          <FileText className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-slate-300 font-medium">{src.document}</p>
                            <p className="text-xs text-slate-500">
                              {src.section} · Page {src.page} · Score {(src.score * 100).toFixed(0)}%
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

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-700 rounded-2xl px-4 py-3">
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="px-4 py-4 bg-slate-800 border-t border-slate-700">
        <div className="max-w-4xl mx-auto flex gap-3 items-end">
          <div className="flex-1 bg-slate-700 rounded-2xl border border-slate-600 focus-within:border-blue-500 transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask FinBot anything about ${user.collections.join(", ")} documents...`}
              rows={1}
              className="w-full bg-transparent text-slate-100 placeholder-slate-500 px-4 py-3 text-sm resize-none focus:outline-none max-h-32 overflow-y-auto"
              style={{ minHeight: "44px" }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-11 h-11 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-xl flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
        <p className="text-center text-slate-600 text-xs mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}