"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, DemoUser } from "@/lib/api";
import { User } from "@/lib/types";
import { Shield, Loader2, Building2 } from "lucide-react";

const ROLE_BADGES: Record<string, { color: string; label: string }> = {
  employee:    { color: "bg-gray-200 text-gray-700",   label: "Employee" },
  finance:     { color: "bg-green-200 text-green-800",  label: "Finance" },
  engineering: { color: "bg-blue-200 text-blue-800",   label: "Engineering" },
  marketing:   { color: "bg-purple-200 text-purple-800", label: "Marketing" },
  c_level:     { color: "bg-amber-200 text-amber-800",  label: "C-Level" },
};

export default function LoginPage() {
  const router = useRouter();
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingUser, setLoadingUser] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Load demo users from API
    authApi.getDemoUsers().then(setDemoUsers).catch(console.error);
    // Clear any existing session
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
        email: res.email,
        name: res.name,
        role: res.role,
        department: res.department,
        collections: res.collections,
        token: res.token,
      } as User));
      router.push("/chat");
    } catch (err) {
      setError("Login failed. Make sure the backend is running.");
    } finally {
      setLoadingUser(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">FinBot</h1>
          <p className="text-slate-400 mt-2">
            Internal Knowledge Assistant · FinSolve Technologies
          </p>
        </div>

        {/* Demo users */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-4 h-4 text-slate-400" />
            <p className="text-slate-400 text-sm">
              Select a demo account to explore role-based access control
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {demoUsers.map((user) => {
              const badge = ROLE_BADGES[user.role];
              const isLoading = loadingUser === user.email;

              return (
                <button
                  key={user.email}
                  onClick={() => handleLogin(user)}
                  disabled={!!loadingUser}
                  className="flex items-center justify-between p-4 bg-slate-700 hover:bg-slate-600 rounded-xl border border-slate-600 hover:border-slate-500 transition-all text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                      {user.name.split(" ").map((n) => n[0]).join("")}
                    </div>
                    <div>
                      <p className="text-white font-medium">{user.name}</p>
                      <p className="text-slate-400 text-sm">{user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${badge.color}`}>
                      {badge.label}
                    </span>
                    {isLoading && (
                      <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <p className="text-slate-500 text-xs text-center mt-4">
            All accounts use password: <span className="font-mono text-slate-400">demo123</span>
          </p>
        </div>
      </div>
    </div>
  );
}