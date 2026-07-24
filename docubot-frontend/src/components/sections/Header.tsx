"use client";

import React, { useState, useEffect } from "react";
import { Menu, X, Moon, Sun } from "lucide-react";
import AuthModal from "../ui/AuthModal";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/Providers";

export default function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const router = useRouter();
  const { isLoggedIn, user, handleLogout } = useAuth();

  useEffect(() => {
    const handleScroll = () => {
      const isScrolled = window.scrollY > 20;
      setScrolled((prev) => (prev !== isScrolled ? isScrolled : prev));
    };
    window.addEventListener("scroll", handleScroll);

    const handleOpenAuth = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail?.mode) {
        setAuthMode(customEvent.detail.mode);
      }
      setIsAuthModalOpen(true);
    };
    window.addEventListener("open-auth-modal", handleOpenAuth);

    // Check initial theme preference
    let themeTimer: NodeJS.Timeout | null = null;
    if (document.documentElement.classList.contains("dark")) {
      themeTimer = setTimeout(() => setIsDark(true), 0);
    }

    return () => {
      window.removeEventListener("scroll", handleScroll);
      window.removeEventListener("open-auth-modal", handleOpenAuth);
      if (themeTimer) clearTimeout(themeTimer);
    };
  }, []);

  const toggleTheme = () => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.remove("dark");
      setIsDark(false);
    } else {
      root.classList.add("dark");
      setIsDark(true);
    }
  };



  const navLinks = [
    { name: "Home", href: "#" },
    { name: "How it works", href: "#how-it-works" },
    { name: "Features", href: "#features" },
    { name: "Pricing", href: "#pricing" },
    { name: "Faq", href: "#faq" },
  ];

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    setIsOpen(false);
    if (typeof window !== "undefined" && window.location.pathname !== "/") {
      router.push("/" + (id === "#" ? "" : id));
      return;
    }
    if (id === "#") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const element = document.querySelector(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-shadow duration-300 border-b border-border bg-background ${scrolled ? "shadow-sm" : ""
        }`}
    >
      <div className="mx-auto box-border flex h-[79px] w-full max-w-[1440px] items-center justify-between px-4 py-2 sm:px-6 md:px-12 lg:px-20 xl:px-[120px]">
        {/* Logo */}
        <a
          href="#"
          className="flex items-center space-x-2"
          onClick={(e) => handleScrollTo(e, "#")}
        >
          <svg className="h-8 w-8 text-[#0052ff]" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
            <circle cx="20" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
            <circle cx="16" cy="12" r="6" fill="currentColor" fillOpacity="0.85" />
            <circle cx="16" cy="20" r="6" fill="currentColor" fillOpacity="0.85" />
            <circle cx="16" cy="16" r="3.5" fill="#ffffff" />
          </svg>
          <span className="text-xl font-extrabold tracking-tight text-foreground transition-colors duration-300">
            DocuBot
          </span>
        </a>

        {/* Desktop Nav Links */}
        <nav className="hidden lg:flex items-center space-x-8">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={(e) => handleScrollTo(e, link.href)}
              className="text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition-colors"
            >
              {link.name}
            </a>
          ))}
        </nav>

        {/* Desktop CTA & Theme Toggle */}
        <div className="hidden lg:flex items-center space-x-4">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          {isLoggedIn ? (
            <div className="relative shrink-0">
              <button
                onClick={() => setIsProfileOpen(!isProfileOpen)}
                className="flex items-center space-x-2.5 hover:opacity-90 transition-all cursor-pointer border-0 bg-transparent p-0"
              >
                <span className="hidden sm:inline-block text-xs font-extrabold text-slate-700 dark:text-slate-200">
                  {user?.full_name || user?.email || "User"}
                </span>
                <div className="w-9 h-9 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-md relative">
                  {user?.full_name 
                    ? user.full_name.split(' ').map((n: any) => n[0]).join('').slice(0, 2).toUpperCase() 
                    : (user?.email ? user.email.slice(0, 2).toUpperCase() : "US")}
                  {/* Active status pulse dot */}
                  <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-white dark:border-[#070b15] rounded-full" />
                </div>
              </button>

              {/* Dropdown Menu */}
              {isProfileOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40 cursor-default"
                    onClick={() => setIsProfileOpen(false)}
                  />
                  <div className="absolute right-0 mt-2.5 w-52 bg-white dark:bg-[#070b15] border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl p-3 z-50 transform origin-top-right transition-all duration-200">
                    <div className="px-2 py-1">
                      <p className="text-xs font-bold text-slate-900 dark:text-white">{user?.full_name || "User"}</p>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5 font-normal font-sans">{user?.email || ""}</p>
                      <span className="inline-block mt-2 text-[9px] bg-slate-100 dark:bg-slate-900 text-[#0052ff] dark:text-[#3b82f6] px-2 py-0.5 rounded-md font-extrabold uppercase tracking-wide">
                        Free Plan
                      </span>
                    </div>
                    <div className="h-[1px] bg-slate-200 dark:bg-white/5 my-2" />
                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        router.push("/dashboard");
                      }}
                      className="w-full flex items-center space-x-2 px-2 py-1.5 rounded-xl text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer border-0 text-left"
                    >
                      <span>Dashboard</span>
                    </button>
                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        handleLogout();
                      }}
                      className="w-full flex items-center space-x-2 px-2 py-1.5 rounded-xl text-xs font-bold text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer border-0 text-left"
                    >
                      <span>Sign Out</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <>
              <button
                className="text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-[#0052ff] dark:hover:text-[#0052ff] transition-colors cursor-pointer"
                onClick={() => {
                  setAuthMode("signin");
                  setIsAuthModalOpen(true);
                }}
              >
                Sign In
              </button>
              <button
                className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-6 py-2.5 rounded-full text-sm font-semibold shadow-sm transition-all cursor-pointer"
                onClick={() => {
                  setAuthMode("signup");
                  setIsAuthModalOpen(true);
                }}
              >
                Sign Up
              </button>
            </>
          )}
        </div>

        {/* Mobile Menu & Theme Button */}
        <div className="flex items-center space-x-3 lg:hidden">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          {isLoggedIn ? (
            <div className="relative shrink-0">
              <button
                onClick={() => setIsProfileOpen(!isProfileOpen)}
                className="flex items-center space-x-2 hover:opacity-90 transition-all cursor-pointer border-0 bg-transparent p-0"
              >
                <span className="hidden sm:inline-block text-xs font-bold text-slate-700 dark:text-slate-200">
                  {user?.full_name || "User"}
                </span>
                <div className="w-8 h-8 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-md relative">
                  {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : "U"}
                  <span className="absolute bottom-0 right-0 w-2 h-2 bg-emerald-500 border border-white dark:border-[#070b15] rounded-full" />
                </div>
              </button>

              {/* Dropdown Menu */}
              {isProfileOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40 cursor-default"
                    onClick={() => setIsProfileOpen(false)}
                  />
                  <div className="absolute right-0 mt-2.5 w-52 bg-white dark:bg-[#070b15] border border-slate-200 dark:border-white/10 rounded-2xl shadow-xl p-3 z-50 transform origin-top-right transition-all duration-200">
                    <div className="px-2 py-1">
                      <p className="text-xs font-bold text-slate-900 dark:text-white">{user?.full_name || "User"}</p>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5 font-normal font-sans">{user?.email || "user@example.com"}</p>
                    </div>
                    <div className="h-[1px] bg-slate-200 dark:bg-white/5 my-2" />
                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        router.push("/dashboard");
                      }}
                      className="w-full flex items-center space-x-2 px-2 py-1.5 rounded-xl text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer border-0 text-left"
                    >
                      <span>Dashboard</span>
                    </button>
                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        handleLogout();
                      }}
                      className="w-full flex items-center space-x-2 px-2 py-1.5 rounded-xl text-xs font-bold text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer border-0 text-left"
                    >
                      <span>Sign Out</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <button
              onClick={() => {
                setAuthMode("signin");
                setIsAuthModalOpen(true);
              }}
              className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-4 py-1.5 rounded-full text-xs font-bold shadow-sm transition-all cursor-pointer border-0"
            >
              Sign In
            </button>
          )}

          <button
            onClick={() => setIsOpen(!isOpen)}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Toggle menu"
          >
            {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {isOpen && (
        <div className="lg:hidden fixed inset-0 top-[79px] z-40 bg-background border-t border-border shadow-xl transition-all duration-300 overflow-y-auto">
          <nav className="flex flex-col p-6 space-y-4">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={(e) => handleScrollTo(e, link.href)}
                className="text-lg font-semibold text-foreground hover:text-[#0052ff] py-2.5 border-b border-border transition-colors"
              >
                {link.name}
              </a>
            ))}
            <div className="pt-4 flex flex-col space-y-3">
              {isLoggedIn ? (
                <>
                  <button
                    className="w-full py-3 rounded-full text-base font-semibold text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    onClick={() => {
                      setIsOpen(false);
                      router.push("/dashboard");
                    }}
                  >
                    Dashboard
                  </button>
                  <button
                    className="w-full bg-[#0052ff] hover:bg-[#003ecc] text-white py-3 rounded-full text-base font-semibold transition-colors cursor-pointer"
                    onClick={handleLogout}
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <button
                    className="w-full py-3 rounded-full text-base font-semibold text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                    onClick={() => {
                      setIsOpen(false);
                      setAuthMode("signin");
                      setIsAuthModalOpen(true);
                    }}
                  >
                    Sign In
                  </button>
                  <button
                    className="w-full bg-[#0052ff] hover:bg-[#003ecc] text-white py-3 rounded-full text-base font-semibold transition-colors cursor-pointer"
                    onClick={() => {
                      setIsOpen(false);
                      setAuthMode("signup");
                      setIsAuthModalOpen(true);
                    }}
                  >
                    Sign Up
                  </button>
                </>
              )}
            </div>
          </nav>
        </div>
      )}

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialMode={authMode}
      />
    </header>
  );
}
