"use client";

import React, { useState, useEffect } from "react";
import { X, Mail, Lock, User, ArrowRight, Phone } from "lucide-react";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/components/providers/Providers";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: "signin" | "signup";
}

export default function AuthModal({ isOpen, onClose, initialMode = "signin" }: AuthModalProps) {
  const [mode, setMode] = useState<"signin" | "signup">(initialMode);
  const [isAnimating, setIsAnimating] = useState(false);
  const [shouldRender, setShouldRender] = useState(false);
  const [isVideoAllowed, setIsVideoAllowed] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { setLoggedIn } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccess("");

    try {
      if (mode === "signin") {
        const res = await fetchApi("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Invalid credentials.");
        }

        // Tokens are securely handled via HttpOnly cookies by the API
        setLoggedIn(true);
        onClose();

      } else {
        const res = await fetchApi("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            full_name: fullName,
          }),
        });

        if (!res.ok) {
          const data = await res.json();
          if (Array.isArray(data.detail)) {
             throw new Error(data.detail[0].msg);
          }
          throw new Error(data.detail || "Registration failed. Please try again.");
        }

        setSuccess("Verification email sent! Please check your inbox.");
        setEmail("");
        setPassword("");
        setFullName("");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "An error occurred. Please try again.");
      } else {
        setError("An error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setIsLoading(true);
    try {
      const res = await fetchApi("/auth/google/verify", {
        method: "POST",
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });
      if (res.ok) {
        setLoggedIn(true);
        onClose();
      } else {
        const data = await res.json();
        setError(data.detail || "Google login failed.");
      }
    } catch (err) {
      console.error("Google sign in verification failed:", err);
      setError("Failed to verify Google Sign In.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      const timer1 = setTimeout(() => {
        setEmail("");
        setPassword("");
        setError("");
        setShouldRender(true);
        setMode(initialMode);

        requestAnimationFrame(() => {
          setIsAnimating(true);
        });
      }, 0);

      // Lazy-load the video after the 500ms slide/scale animation completes
      const timer2 = setTimeout(() => {
        setIsVideoAllowed(true);
      }, 550);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    } else {
      const timer1 = setTimeout(() => {
        setIsAnimating(false);
        setIsVideoAllowed(false);
      }, 0);
      const timer2 = setTimeout(() => {
        setShouldRender(false);
      }, 500); // match transition duration (500ms)
      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    }
  }, [isOpen, initialMode]);

  if (!shouldRender) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-300 ${isAnimating ? "opacity-100" : "opacity-0"
          }`}
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`relative w-full max-w-5xl h-[90vh] max-h-[580px] md:h-[680px] md:max-h-none overflow-hidden rounded-3xl bg-white dark:bg-slate-900 shadow-2xl transition-all duration-500 ease-in-out flex flex-col md:block ${isAnimating ? "opacity-100 scale-100 translate-y-0" : "opacity-0 scale-95 translate-y-4"
          }`}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm shadow-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white transition-colors z-[60]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Branding Panel (Slides Left/Right on Desktop, hidden on Mobile) */}
        <div
          className={`hidden md:flex w-full h-[120px] md:h-full md:absolute md:top-0 md:left-0 md:w-1/2 bg-[#0052ff] p-4 md:p-10 text-white flex-col justify-between overflow-hidden z-20 transition-all duration-500 ease-in-out ${mode === "signup" ? "md:translate-x-full" : "md:translate-x-0"
            }`}
        >
          {/* Subtle background glow elements */}
          <div className="absolute -top-24 -left-24 w-96 h-96 bg-white opacity-10 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-black opacity-10 rounded-full blur-3xl pointer-events-none"></div>

          {/* Logo */}
          <div className="flex items-center space-x-2 mb-2 md:mb-0 md:absolute md:top-10 md:left-10 z-30">
            <svg className="h-6 w-6 md:h-8 md:w-8 text-white" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="20" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="12" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="20" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="16" r="3.5" fill="#0052ff" />
            </svg>
            <span className="text-lg md:text-xl font-extrabold tracking-tight text-white">
              DocuBot
            </span>
          </div>

          <div className="relative z-10 flex-1 flex flex-col justify-center">

            {/* Title / Description Transitions */}
            <div className="relative h-12 md:h-[130px]">
              <div className={`transition-all duration-500 ease-in-out absolute top-0 left-0 w-full ${mode === "signin" ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8 pointer-events-none"
                }`}>
                <h3 className="text-lg md:text-3xl font-bold mb-1 md:mb-4 leading-tight">Welcome back to the future.</h3>
                <p className="hidden md:block text-blue-100 text-sm md:text-base leading-relaxed">
                  Log in to continue building amazing experiences with our platform. We&apos;re glad to see you again.
                </p>
              </div>
              <div className={`transition-all duration-500 ease-in-out absolute top-0 left-0 w-full ${mode === "signup" ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8 pointer-events-none"
                }`}>
                <h3 className="text-lg md:text-3xl font-bold mb-1 md:mb-4 leading-tight">Start your journey with us.</h3>
                <p className="hidden md:block text-blue-100 text-sm md:text-base leading-relaxed">
                  Join thousands of users who are already building the future with our advanced tools.
                </p>
              </div>
            </div>

            {/* Single Shared & Lazy-Loaded Video Player */}
            {isVideoAllowed && (
              <div
                className="mt-6 hidden md:flex justify-center w-full"
                style={{ mixBlendMode: "screen", transform: "translate3d(0,0,0)" }}
              >
                <video
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full max-w-[460px] h-[360px] object-contain opacity-95"
                  style={{
                    mixBlendMode: "screen",
                    transform: "scale(1.6) translateX(-95px) translateY(-75px) translate3d(0,0,0)"
                  }}
                >
                  <source src="/images/chat bot icon3.webm" type="video/webm" />
                  <source src="/images/chat bot icon3.mp4" type="video/mp4" />
                  <source src="/images/chat bot icon3.webm.mov" type="video/quicktime" />
                </video>
              </div>
            )}
          </div>

          <div className="relative z-10 text-[10px] md:text-xs text-blue-200 hidden md:block md:absolute md:bottom-10 md:left-10">
            © 2026 DocuBot. All rights reserved.
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SIGN IN FORM CONTAINER                                                    */}
        {/* ========================================================================= */}
        <div
          className={`absolute left-0 right-0 bottom-0 top-0 md:left-1/2 md:w-1/2 md:h-full p-4 sm:p-8 md:p-10 bg-white dark:bg-slate-900 z-10 transition-all duration-500 ease-in-out flex flex-col justify-start md:justify-center overflow-y-auto md:overflow-visible ${mode === "signin"
            ? "translate-x-0 opacity-100 pointer-events-auto"
            : "translate-x-full md:translate-x-0 md:opacity-0 md:pointer-events-none opacity-0 pointer-events-none"
            }`}
        >
          {/* Mobile Logo Brand */}
          <div className="md:hidden flex items-center space-x-2 mb-4 shrink-0">
            <svg className="h-6 w-6 text-[#0052ff]" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="20" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="12" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="20" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="16" r="3.5" fill="#0052ff" />
            </svg>
            <span className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white">
              DocuBot
            </span>
          </div>

          <div className="mb-3 md:mb-6 mt-1 md:mt-0">
            <div className="w-7 h-7 md:w-10 md:h-10 bg-blue-50 dark:bg-[#0052ff]/10 rounded-xl md:rounded-2xl flex items-center justify-center mb-1.5 md:mb-4 border border-blue-100 dark:border-[#0052ff]/20">
              <Lock className="w-3.5 h-3.5 md:w-5 md:h-5 text-[#0052ff]" />
            </div>
            <h2 className="text-lg md:text-[26px] font-extrabold text-slate-900 dark:text-white mb-0.5 md:mb-2 tracking-tight">
              Welcome back
            </h2>
            <p className="text-[11px] md:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              Enter your details below to access your account. <span className="text-[#0052ff] font-semibold block mt-0.5 md:mt-1 font-sans">Hint: admin@docubot.ai / password123</span>
            </p>
          </div>

          {error && (
            <div className="mb-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 dark:text-red-400 text-xs font-semibold text-center">
              {error}
            </div>
          )}

          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1">
              <label className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-300">Email Address</label>
              <div className="relative group">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
                <input
                  type="email"
                  required
                  placeholder="Enter Email Address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 md:py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-xs md:text-sm text-slate-900 dark:text-white transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-300">Password</label>
                <a href="#" className="text-[10px] md:text-xs font-medium text-[#0052ff] hover:text-[#003ecc] transition-all">
                  Forgot password?
                </a>
              </div>
              <div className="relative group">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 md:py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-xs md:text-sm text-slate-900 dark:text-white transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <button disabled={isLoading} className="w-full flex items-center justify-center space-x-2 bg-[#0052ff] hover:bg-[#003ecc] text-white py-2.5 md:py-3 rounded-xl font-semibold shadow-lg shadow-[#0052ff]/25 transition-all active:scale-[0.98] mt-3 md:mt-4 group text-xs md:text-sm disabled:opacity-70">
              <span>{isLoading ? "Signing In..." : "Sign In"}</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-3 md:mt-6 mb-2 md:mb-5 relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-800"></div>
            </div>
            <div className="relative flex justify-center text-[10px] md:text-xs">
              <span className="px-2 bg-white dark:bg-slate-900 text-slate-500 font-sans">Or continue with</span>
            </div>
          </div>

          <div className="flex justify-center w-full">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError("Google Sign In failed.")}
              text="signin_with"
              size="large"
              width="100%"
              theme="outline"
              logo_alignment="center"
            />
          </div>

          <p className="mt-3 md:mt-6 text-center text-xs md:text-sm text-slate-500 dark:text-slate-400">
            Don&apos;t have an account?{" "}
            <button
              className="font-semibold text-[#0052ff] hover:text-[#003ecc] transition-colors"
              onClick={() => setMode("signup")}
            >
              Sign up
            </button>
          </p>
        </div>

        {/* ========================================================================= */}
        {/* SIGN UP FORM CONTAINER                                                    */}
        {/* ========================================================================= */}
        <div
          className={`absolute left-0 right-0 bottom-0 top-0 md:left-0 md:w-1/2 md:h-full p-4 sm:p-8 md:p-10 bg-white dark:bg-slate-900 z-10 transition-all duration-500 ease-in-out flex flex-col justify-start md:justify-center overflow-y-auto md:overflow-visible ${mode === "signup"
            ? "translate-x-0 opacity-100 pointer-events-auto"
            : "-translate-x-full md:translate-x-0 md:opacity-0 md:pointer-events-none opacity-0 pointer-events-none"
            }`}
        >
          {/* Mobile Logo Brand */}
          <div className="md:hidden flex items-center space-x-2 mb-4 shrink-0">
            <svg className="h-6 w-6 text-[#0052ff]" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="20" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="12" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="20" r="6" fill="currentColor" fillOpacity="0.85" />
              <circle cx="16" cy="16" r="3.5" fill="#0052ff" />
            </svg>
            <span className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white">
              DocuBot
            </span>
          </div>

          <div className="mb-3 md:mb-6 mt-1 md:mt-0">
            <div className="w-7 h-7 md:w-10 md:h-10 bg-blue-50 dark:bg-[#0052ff]/10 rounded-xl md:rounded-2xl flex items-center justify-center mb-1.5 md:mb-4 border border-blue-100 dark:border-[#0052ff]/20">
              <User className="w-3.5 h-3.5 md:w-5 md:h-5 text-[#0052ff]" />
            </div>
            <h2 className="text-lg md:text-[26px] font-extrabold text-slate-900 dark:text-white mb-0.5 md:mb-2 tracking-tight">
              Create an account
            </h2>
            <p className="text-[11px] md:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              Join us today and get started with your new account.
            </p>
          </div>

          {error && (
            <div className="mb-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 dark:text-red-400 text-xs font-semibold text-center">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-3 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-500 dark:text-green-400 text-xs font-semibold text-center">
              {success}
            </div>
          )}

          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1">
              <label className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-300">Full Name</label>
              <div className="relative group">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Enter Your Full Name"
                  className="w-full pl-9 pr-3 py-2 md:py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-xs md:text-sm text-slate-900 dark:text-white transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-300">Email Address</label>
              <div className="relative group">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter Your Email Address"
                  className="w-full pl-9 pr-3 py-2 md:py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-xs md:text-sm text-slate-900 dark:text-white transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs md:text-sm font-semibold text-slate-700 dark:text-slate-300">Password</label>
              <div className="relative group">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#0052ff] transition-colors" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 md:py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff]/20 focus:border-[#0052ff] text-xs md:text-sm text-slate-900 dark:text-white transition-all placeholder:text-slate-400"
                />
              </div>
            </div>

            <button disabled={isLoading} className="w-full flex items-center justify-center space-x-2 bg-[#0052ff] hover:bg-[#003ecc] text-white py-2.5 md:py-3 rounded-xl font-semibold shadow-lg shadow-[#0052ff]/25 transition-all active:scale-[0.98] mt-3 md:mt-4 group text-xs md:text-sm disabled:opacity-70">
              <span>{isLoading ? "Creating..." : "Create Account"}</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>

          <div className="mt-3 md:mt-6 mb-2 md:mb-5 relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-800"></div>
            </div>
            <div className="relative flex justify-center text-[10px] md:text-xs">
              <span className="px-2 bg-white dark:bg-slate-900 text-slate-500 font-sans">Or continue with</span>
            </div>
          </div>

          <div className="flex justify-center w-full">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError("Google Sign In failed.")}
              text={mode === "signin" ? "signin_with" : "signup_with"}
              size="large"
              width="100%"
              theme="outline"
              logo_alignment="center"
            />
          </div>

          <p className="mt-3 md:mt-6 text-center text-xs md:text-sm text-slate-500 dark:text-slate-400">
            Already have an account?{" "}
            <button
              className="font-semibold text-[#0052ff] hover:text-[#003ecc] transition-colors"
              onClick={() => setMode("signin")}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
