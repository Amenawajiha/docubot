"use client";

import React, { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Lock, ArrowRight, CheckCircle2 } from "lucide-react";
import { fetchApi } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const router = useRouter();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!token) {
      setError("Invalid or missing reset token.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetchApi("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to reset password. Please try again.");
      }

      setSuccess(true);
      setTimeout(() => {
        router.push("/");
      }, 3000);
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="w-full max-w-md mx-auto p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 text-center animate-fadeIn relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-400"></div>
        <div className="w-16 h-16 bg-green-50 dark:bg-green-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6 mt-4">
          <CheckCircle2 className="w-8 h-8 text-green-500" />
        </div>
        <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white mb-2 tracking-tight">Password Reset</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
          Your password has been successfully reset. Redirecting you to login...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 animate-fadeIn relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#0052ff] to-blue-400"></div>
      
      <div className="flex items-center space-x-2.5 mb-8 shrink-0 w-full justify-center mt-2">
        <img src="/images/vedios/Synq.svg" alt="SYNQDOC Logo" className="h-10 w-10 shrink-0 object-contain drop-shadow-sm" />
        <span className="text-xl font-black tracking-tight text-slate-900 dark:text-white">
          SYN<span className="text-[#0052ff]">Q</span>DOC
        </span>
      </div>

      <div className="mb-6">
        <h2 className="text-[26px] font-extrabold text-slate-900 dark:text-white mb-2 tracking-tight text-center">
          Set New Password
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
          Please enter your new password below.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 dark:text-red-400 text-xs font-semibold text-center">
          {error}
        </div>
      )}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">New Password</label>
          <div className="relative group">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-sm text-slate-900 dark:text-white transition-all"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-slate-700 dark:text-slate-300">Confirm Password</label>
          <div className="relative group">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
            <input
              type="password"
              required
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-sm text-slate-900 dark:text-white transition-all"
            />
          </div>
        </div>

        <button disabled={isLoading} className="w-full flex items-center justify-center space-x-2 bg-[#0052ff] hover:bg-[#003ecc] text-white py-3 rounded-xl font-semibold shadow-lg shadow-[#0052ff]/25 transition-all active:scale-[0.98] mt-2 group text-sm disabled:opacity-70">
          <span>{isLoading ? "Resetting..." : "Reset Password"}</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 dark:bg-slate-950 p-4 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#0052ff] opacity-[0.03] dark:opacity-[0.05] rounded-full blur-[100px] pointer-events-none"></div>
      
      <Suspense fallback={
        <div className="w-full max-w-md mx-auto p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 animate-pulse h-[450px]">
        </div>
      }>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
