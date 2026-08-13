"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutGrid,
  Bot,
  FileText,
  Globe,
  BarChart3,
  Brain,
  Settings as SettingsIcon,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  CreditCard,
  X,
  LogOut,
  Terminal
} from "lucide-react";
import { useWorkspace, useAuth } from "@/components/providers/Providers";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  
  const {
    sidebarOpen,
    setSidebarOpen,
    sidebarCollapsed,
    setSidebarCollapsed,
    workspaceId,
    currentChatbot
  } = useWorkspace();

  const { user, handleLogout } = useAuth();
  const [showWhatsNew, setShowWhatsNew] = useState(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem("dismissedWhatsNew") !== "true";
    }
    return true;
  });

  const mainItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutGrid, path: `/dashboard/${workspaceId}` },
    { id: "chatbots", label: "My chatbots", icon: Bot, path: `/dashboard/${workspaceId}/bots` },
    { id: "all-documents", label: "All Documents", icon: FileText, path: `/dashboard/${workspaceId}/all-documents` }
  ];

  const botConfigItems = currentChatbot
    ? [
        { id: "studio", label: "Bot Studio", icon: Bot, path: `/dashboard/${workspaceId}/bots/${currentChatbot.id}/settings` },
        { id: "playground", label: "Playground", icon: Terminal, path: `/dashboard/${workspaceId}/bots/${currentChatbot.id}/playground` },
        { id: "knowledge", label: "Knowledge base", icon: Brain, path: `/dashboard/${workspaceId}/bots/${currentChatbot.id}/knowledge` },
        { id: "deployment", label: "Deployment", icon: Globe, path: `/dashboard/${workspaceId}/bots/${currentChatbot.id}/deployment` },
        { id: "reporting", label: "Reporting", icon: BarChart3, path: `/dashboard/${workspaceId}/bots/${currentChatbot.id}/analytics` }
      ]
    : [];

  const accountItems = [
    { id: "billing", label: "Billing", icon: CreditCard, path: `/dashboard/${workspaceId}/billing` },
    { id: "settings", label: "Settings", icon: SettingsIcon, path: `/dashboard/${workspaceId}/settings` },
    {
      id: "support",
      label: "Help and Support",
      icon: HelpCircle,
      path: `/dashboard/${workspaceId}/support`
    },
    {
      id: "logout",
      label: "Logout",
      icon: LogOut,
      isButton: true,
      onClick: handleLogout
    }
  ];

  const renderItem = (item: typeof accountItems[0]) => {
    const Icon = item.icon;
    const isActive = item.path
      ? pathname === item.path || (item.id === "studio" && currentChatbot && pathname === `/dashboard/${workspaceId}/bots/${currentChatbot.id}`)
      : false;

    const content = sidebarCollapsed ? (
      <Icon className="w-4.5 h-4.5 shrink-0" />
    ) : (
      <div className="flex items-center space-x-3 overflow-hidden">
        <Icon className="w-4 h-4 shrink-0" />
        <span className="truncate">{item.label}</span>
      </div>
    );

    const classes = sidebarCollapsed
      ? `w-11 h-11 mx-auto flex items-center justify-center rounded-xl transition-all cursor-pointer border-0 ${
          isActive
            ? "bg-[#0D53FC] text-white shadow-md shadow-[#0D53FC]/20"
            : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 bg-transparent"
        }`
      : `w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-semibold transition-all cursor-pointer border-0 text-left ${
          isActive
            ? "bg-[#0D53FC] text-white shadow-md shadow-[#0D53FC]/20"
            : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 bg-transparent"
        }`;

    if (item.isButton || !item.path) {
      return (
        <button
          key={item.id}
          onClick={() => {
            setSidebarOpen(false);
            if (item.onClick) item.onClick();
          }}
          className={classes}
        >
          {content}
        </button>
      );
    }

    return (
      <Link
        key={item.id}
        href={item.path}
        onClick={() => setSidebarOpen(false)}
        className={classes}
      >
        {content}
      </Link>
    );
  };

  const renderSectionHeader = (label: string) => {
    if (sidebarCollapsed) return <div className="h-[1px] bg-slate-200 dark:bg-white/5 my-3" />;
    return (
      <div className="px-3.5 pt-4 pb-1.5 text-[10px] font-extrabold uppercase tracking-wider text-slate-450 dark:text-slate-500">
        {label}
      </div>
    );
  };

  return (
    <>
      {/* Backdrop overlay for mobile drawer */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden fixed inset-0 bg-black/40 z-45 backdrop-blur-sm transition-opacity"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 transform ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 lg:sticky transition-all duration-300 ease-in-out z-50 ${
          sidebarCollapsed ? "w-20" : "w-64"
        } bg-white dark:bg-[#070b15] border-r border-slate-200 dark:border-white/5 flex flex-col justify-between shrink-0 h-screen transition-colors duration-300`}
      >
        {/* Floating Sidebar Collapse Toggle Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="hidden lg:flex absolute top-[28px] -right-3.5 z-55 p-1 bg-white dark:bg-[#070b15] border border-slate-200 dark:border-white/10 rounded-full text-slate-500 hover:text-slate-800 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer shadow-sm shadow-black/5"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        <div className="flex flex-col flex-1 overflow-y-auto min-h-0 relative">
          {/* Sidebar Header Brand */}
          <div className={`h-[79px] border-b border-slate-200 dark:border-white/5 flex items-center shrink-0 ${
            sidebarCollapsed ? "justify-center px-2" : "justify-between px-5"
          }`}>
            <Link
              href="/"
              className="flex items-center space-x-2 overflow-hidden hover:opacity-85 transition-opacity cursor-pointer shrink-0"
            >
              <svg className="h-8 w-8 text-[#0D53FC] shrink-0" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
                <circle cx="20" cy="16" r="6" fill="currentColor" fillOpacity="0.85" />
                <circle cx="16" cy="12" r="6" fill="currentColor" fillOpacity="0.85" />
                <circle cx="16" cy="20" r="6" fill="currentColor" fillOpacity="0.85" />
                <circle cx="16" cy="16" r="3.5" fill="#ffffff" />
              </svg>
              {!sidebarCollapsed && (
                <span className="text-xl font-extrabold tracking-tight text-slate-900 dark:text-white truncate transition-colors duration-300">
                  DocuBot
                </span>
              )}
            </Link>
            
            {/* Mobile close button only */}
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full text-slate-500 transition-colors cursor-pointer shrink-0 border border-slate-200/50 dark:border-white/5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className={`space-y-4 pt-4 flex-1 text-left overflow-y-auto ${
            sidebarCollapsed ? "px-2" : "p-4"
          }`}>
            {/* MAIN section */}
            <div>
              {renderSectionHeader("MAIN")}
              <div className="space-y-1 mt-1">
                {mainItems.map(renderItem)}
              </div>
            </div>

            {/* BOT CONFIGURATION section */}
            {botConfigItems.length > 0 && (
              <div>
                {renderSectionHeader("BOT CONFIGURATION")}
                <div className="space-y-1 mt-1">
                  {botConfigItems.map(renderItem)}
                </div>
              </div>
            )}

            {/* ACCOUNT section */}
            <div>
              {renderSectionHeader("ACCOUNT")}
              <div className="space-y-1 mt-1">
                {accountItems.map(renderItem)}
              </div>
            </div>
          </nav>
        </div>

        {/* Sidebar Bottom Card & User Profile */}
        <div className="shrink-0 flex flex-col">
          {/* What's New Card */}
          {!sidebarCollapsed && showWhatsNew && (
            <div className="mx-4 mb-4 p-4 rounded-2xl bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100/50 dark:border-blue-950/30 text-left space-y-3.5 animate-fadeIn">
              <div className="flex items-center space-x-2 text-[#0052ff] dark:text-blue-400 font-bold">
                <Sparkles className="w-4 h-4 text-[#0052ff] dark:text-blue-400" />
                <span className="text-xs">What&apos;s New</span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                Bot Studio upgrades, faster document indexing, and new Slack deployment options.
              </p>
              <div className="flex items-center space-x-3 pt-1">
                <button
                  onClick={() => alert("Opening release updates details...")}
                  className="bg-[#0052ff] hover:bg-[#003ecc] text-[#ffffff] px-3 py-1.5 rounded-xl text-[10px] font-bold border-0 cursor-pointer transition-colors shadow-sm"
                >
                  View updates
                </button>
                <button
                  onClick={() => {
                    setShowWhatsNew(false);
                    sessionStorage.setItem("dismissedWhatsNew", "true");
                  }}
                  className="text-[10px] text-slate-500 hover:text-slate-700 dark:hover:text-slate-350 bg-transparent border-0 cursor-pointer font-bold"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* User Profile Footer connected to GET /auth/me */}
          <div className="p-3 border-t border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-slate-900/30">
            {sidebarCollapsed ? (
              <div
                onClick={() => router.push(`/dashboard/${workspaceId}/settings`)}
                title={user?.full_name || "User Profile"}
                className="w-10 h-10 mx-auto rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white flex items-center justify-center font-bold text-xs relative cursor-pointer hover:opacity-90 transition-opacity shadow-sm"
              >
                {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : "U"}
                <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-white dark:border-[#070b15] rounded-full" />
              </div>
            ) : (
              <div
                onClick={() => router.push(`/dashboard/${workspaceId}/settings`)}
                className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 transition-colors cursor-pointer"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="w-9 h-9 rounded-full bg-[#0052ff] text-white flex items-center justify-center font-bold text-xs shrink-0 relative shadow-sm">
                    {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : "U"}
                    <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-white dark:border-[#070b15] rounded-full" />
                  </div>
                  <div className="min-w-0 text-left">
                    <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                      {user?.full_name || "User"}
                    </p>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                      {user?.email || "user@docubot.ai"}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}