"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, UserPlus, Building2, Search, Bot, Check, Plus } from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";
import { StatusBadge } from "@/components/ui/shared-dashboard";

export default function Header() {
  const router = useRouter();
  const {
    workspaceId,
    workspaces,
    chatbots,
    currentChatbot,
    changeCurrentChatbot,
  } = useWorkspace();

  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);
  const [isMembersOpen, setIsMembersOpen] = useState(false);
  const [botSearchQuery, setBotSearchQuery] = useState("");

  const workspaceRef = useRef<HTMLDivElement>(null);
  const chatbotRef = useRef<HTMLDivElement>(null);
  const membersRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (workspaceRef.current && !workspaceRef.current.contains(e.target as Node)) {
        setIsWorkspaceOpen(false);
      }
      if (chatbotRef.current && !chatbotRef.current.contains(e.target as Node)) {
        setIsChatbotOpen(false);
      }
      if (membersRef.current && !membersRef.current.contains(e.target as Node)) {
        setIsMembersOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentWorkspace = workspaces.find((w) => w.id === workspaceId) || workspaces[0];

  const getBotStatus = (bot: typeof chatbots[0]) => {
    if (bot.deployment_status === "published" || bot.status === "Active") return "Active";
    if (bot.deployment_status === "archived" || bot.status === "Inactive") return "Archived";
    return "Draft";
  };

  const getUpdatedString = (bot: typeof chatbots[0]) => {
    if (bot.updated_at || bot.created) {
      const updatedTime = new Date(bot.updated_at || bot.created || "");
      const diffMs = new Date().getTime() - updatedTime.getTime();
      const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHrs / 24);
      if (diffDays > 0) return `Edited ${diffDays}d ago`;
      else if (diffHrs > 0) return `Edited ${diffHrs}h ago`;
    }
    return "Edited 5 min ago";
  };

  const filteredBots = chatbots.filter((b) =>
    b.name.toLowerCase().includes(botSearchQuery.toLowerCase())
  );

  const mockMembers = [
    { initials: "JD", name: "Jane Doe", role: "Owner", color: "rgb(0, 82, 255)" },
    { initials: "MR", name: "Marcus Rivera", role: "Admin", color: "rgb(5, 177, 105)" },
    { initials: "PK", name: "Priya Kapoor", role: "Editor", color: "rgb(244, 176, 0)" },
    { initials: "AC", name: "Alex Chen", role: "Viewer", color: "rgb(124, 130, 138)" },
  ];

  return (
    <header className="h-14 border-b border-slate-200 dark:border-white/5 bg-white dark:bg-[#070b15] sticky top-0 z-40 w-full shrink-0">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Left: Workspace Selector & Chatbot Selector */}
        <div className="flex items-center gap-3 min-w-0">
          {/* 1. Workspace Selector (connected to GET /workspaces) */}
          <div className="relative" ref={workspaceRef}>
            <button
              onClick={() => setIsWorkspaceOpen(!isWorkspaceOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#0a0b0d] dark:text-white hover:bg-slate-50 dark:hover:bg-white/5 transition-all select-none cursor-pointer"
            >
              <Building2 size={13} className="text-[#0052ff]" />
              <span className="truncate max-w-[140px]">{currentWorkspace?.name || "Acme Corp"}</span>
              <ChevronDown size={12} className="text-slate-400 shrink-0" />
            </button>

            {isWorkspaceOpen && workspaces && workspaces.length > 0 && (
              <div className="absolute left-0 top-full mt-1.5 w-56 bg-white dark:bg-[#0d111b] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl py-1.5 z-50">
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setIsWorkspaceOpen(false);
                      router.push(`/dashboard/${ws.id}`);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-white/5 flex items-center justify-between border-0 bg-transparent cursor-pointer ${
                      workspaceId === ws.id ? "font-semibold text-[#0052ff]" : "text-slate-700 dark:text-slate-350"
                    }`}
                  >
                    <span className="truncate">{ws.name}</span>
                    {workspaceId === ws.id && <span className="w-1.5 h-1.5 rounded-full bg-[#0052ff]" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 2. Chatbot Switcher Selector */}
          <div className="relative" ref={chatbotRef}>
            <button
              onClick={() => setIsChatbotOpen(!isChatbotOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[#dee1e6] dark:border-white/10 hover:border-[#0052ff]/40 hover:bg-[#f0f5ff] dark:hover:bg-white/5 transition-all group bg-white dark:bg-[#0d111b] cursor-pointer"
              aria-haspopup="listbox"
              aria-expanded={isChatbotOpen}
              aria-label="Select chatbot"
            >
              <div
                className="w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[10px] text-white font-bold"
                style={{ backgroundColor: currentChatbot?.color || "#0052ff" }}
              >
                {currentChatbot?.avatarEmoji || "🤖"}
              </div>
              <span className="font-semibold text-sm text-[#0a0b0d] dark:text-white max-w-36 truncate">
                {currentChatbot?.name || "Support Assistant"}
              </span>
              <StatusBadge status={currentChatbot ? getBotStatus(currentChatbot) : "Draft"} />
              <ChevronDown
                size={13}
                className={`text-[#7c828a] shrink-0 transition-transform ${isChatbotOpen ? "rotate-180" : ""}`}
              />
              <span className="ml-1 text-[10px] font-mono text-[#a8acb3] hidden group-hover:inline">⌘K</span>
            </button>

            {isChatbotOpen && (
              <div className="absolute top-full mt-2 w-72 bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/10 shadow-xl z-50 overflow-hidden left-0">
                <div className="p-3 border-b border-[#dee1e6] dark:border-white/10">
                  <p className="px-1 pb-2 text-xs font-semibold text-[#0a0b0d] dark:text-white text-left">Select Chatbot</p>
                  <div className="flex items-center gap-2 px-3 py-2 bg-[#f7f7f7] dark:bg-slate-900 rounded-xl">
                    <Search size={13} className="text-[#a8acb3] shrink-0" />
                    <input
                      className="flex-1 text-sm bg-transparent outline-none placeholder-[#a8acb3] text-[#0a0b0d] dark:text-white"
                      placeholder="Search chatbots…"
                      aria-label="Search chatbots"
                      value={botSearchQuery}
                      onChange={(e) => setBotSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
                <div className="py-1 max-h-64 overflow-y-auto" role="listbox">
                  <p className="px-4 py-1.5 text-[10px] font-semibold text-[#a8acb3] uppercase tracking-wider text-left">Recent</p>
                  {filteredBots.map((bot) => {
                    const isSelected = currentChatbot?.id === bot.id;
                    const botStatus = getBotStatus(bot);
                    return (
                      <button
                        key={bot.id}
                        role="option"
                        aria-selected={isSelected}
                        onClick={() => {
                          changeCurrentChatbot(bot.id);
                          setIsChatbotOpen(false);
                        }}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors text-left border-0 cursor-pointer ${
                          isSelected ? "bg-[#f0f5ff] dark:bg-blue-950/20" : "bg-transparent"
                        }`}
                      >
                        <div
                          className="w-7 h-7 rounded-full shrink-0 flex items-center justify-center"
                          style={{ backgroundColor: `${bot.color || "#0052ff"}20` }}
                        >
                          <Bot size={13} style={{ color: bot.color || "#0052ff" }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white truncate">{bot.name}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <StatusBadge status={botStatus} />
                            <span className="text-[10px] text-[#a8acb3]">{getUpdatedString(bot)}</span>
                          </div>
                        </div>
                        {isSelected && <Check size={13} className="text-[#0052ff] shrink-0" />}
                      </button>
                    );
                  })}
                </div>
                <div className="border-t border-[#dee1e6] dark:border-white/10 p-2">
                  <button
                    onClick={() => {
                      setIsChatbotOpen(false);
                      router.push(`/dashboard/${workspaceId}/bots/new`);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors text-sm font-semibold text-[#0052ff] border-0 bg-transparent cursor-pointer"
                  >
                    <Plus size={14} className="shrink-0" /> Create New Chatbot
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Members Stack & Invite Button */}
        {/* 
        <div className="flex items-center gap-4 shrink-0">
          <div className="relative flex items-center gap-2" ref={membersRef}>
            <button
              onClick={() => setIsMembersOpen(!isMembersOpen)}
              className="flex items-center -space-x-2 hover:opacity-90 transition-opacity border-0 bg-transparent p-0 cursor-pointer"
              aria-label="Workspace members"
            >
              <div className="w-6 h-6 text-[9px] rounded-full border-2 border-white dark:border-[#070b15] flex items-center justify-center text-white font-bold bg-[#0052ff]">JD</div>
              <div className="w-6 h-6 text-[9px] rounded-full border-2 border-white dark:border-[#070b15] flex items-center justify-center text-white font-bold bg-[#05b169]">MR</div>
              <div className="w-6 h-6 text-[9px] rounded-full border-2 border-white dark:border-[#070b15] flex items-center justify-center text-white font-bold bg-[#f4b000]">PK</div>
              <div className="w-6 h-6 text-[9px] rounded-full border-2 border-white dark:border-[#070b15] bg-[#eef0f3] dark:bg-slate-800 flex items-center justify-center text-[#5b616e] dark:text-slate-300 font-semibold">+1</div>
            </button>

            {isMembersOpen && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl shadow-xl py-2 z-50">
                <p className="px-3 py-1.5 text-[10px] font-semibold text-[#7c828a] uppercase tracking-wider text-left">
                  Workspace members
                </p>
                {mockMembers.map((member) => (
                  <div key={member.name} className="flex items-center gap-2.5 px-3 py-2 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0"
                      style={{ backgroundColor: member.color }}
                    >
                      {member.initials}
                    </div>
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-xs font-semibold text-[#0a0b0d] dark:text-white truncate">{member.name}</p>
                      <p className="text-[10px] text-[#7c828a]">{member.role}</p>
                    </div>
                  </div>
                ))}
                <button
                  onClick={() => {
                    setIsMembersOpen(false);
                    router.push(`/dashboard/${workspaceId}/team?invite=true`);
                  }}
                  className="w-full mx-2 mt-1 flex items-center justify-center gap-1.5 h-8 px-3 rounded-full bg-[#0052ff] text-white text-xs font-semibold hover:bg-[#003ecc] transition-colors border-0 cursor-pointer"
                  style={{ width: "calc(100% - 16px)" }}
                >
                  <UserPlus size={12} /> Invite member
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => router.push(`/dashboard/${workspaceId}/team?invite=true`)}
            className="flex items-center gap-1.5 h-8 px-4 rounded-full text-xs font-semibold text-[#5b616e] dark:text-slate-350 hover:bg-slate-100 dark:hover:bg-white/5 border border-slate-200 dark:border-white/10 transition-colors shadow-sm cursor-pointer bg-white dark:bg-[#0d111b]"
          >
            <UserPlus size={12} className="shrink-0" /> Invite
          </button>
        </div>
        */}
      </div>
    </header>
  );
}
