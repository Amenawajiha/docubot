"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bot, Plus, MessageSquare, Star, Clock, Cpu,
  FlaskConical, Settings, Rocket,
} from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { StatusBadge, BotOverflowMenu, Toast } from "@/components/ui/shared-dashboard";

export default function BotList() {
  const router = useRouter();
  const { workspaceId, chatbots, setChatbots } = useWorkspace();
  const [filter, setFilter] = useState("All");

  // Inline rename & notification states
  const [editingBotId, setEditingBotId] = useState<string | null>(null);
  const [editingBotName, setEditingBotName] = useState("");
  const [toastMsg, setToastMsg] = useState("");
  const [toastVisible, setToastVisible] = useState(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2500);
  };

  // Helper to map backend deployment_status to UI status safely
  const getUiStatus = (bot: typeof chatbots[0]) => {
    if (bot.deployment_status === "published" || bot.status === "Active") return "Active";
    if (bot.deployment_status === "archived" || bot.status === "Inactive") return "Archived";
    return "Draft";
  };

  const filtered = filter === "All"
    ? chatbots
    : chatbots.filter((b) => getUiStatus(b) === filter);

  // Helper to format date
  const getUpdatedString = (bot: typeof chatbots[0]) => {
    if (bot.updated_at || bot.created) {
      const updatedTime = new Date(bot.updated_at || bot.created || "");
      const diffMs = new Date().getTime() - updatedTime.getTime();
      const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHrs / 24);
      
      if (diffDays > 0) return `${diffDays}d ago`;
      else if (diffHrs > 0) return `${diffHrs}h ago`;
    }
    return "recently";
  };

  // Action: Save Rename via PATCH API
  const handleSaveRename = async (botId: string) => {
    const trimmedName = editingBotName.trim();
    if (!trimmedName || !workspaceId) {
      setEditingBotId(null);
      return;
    }

    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: trimmedName }),
      });
      if (res.ok) {
        setChatbots((prev) =>
          prev.map((b) => (b.id === botId ? { ...b, name: trimmedName } : b))
        );
        showToast("Chatbot renamed successfully");
      }
    } catch (err) {
      console.error("Failed to rename chatbot", err);
    } finally {
      setEditingBotId(null);
    }
  };

  // Action: Archive Chatbot via PATCH API
  const handleArchiveBot = async (botId: string) => {
    if (!workspaceId) return;
    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}`, {
        method: "PATCH",
        body: JSON.stringify({ deployment_status: "archived" }),
      });
      if (res.ok) {
        setChatbots((prev) =>
          prev.map((b) => (b.id === botId ? { ...b, deployment_status: "archived" } : b))
        );
        showToast("Chatbot archived");
      }
    } catch (err) {
      console.error("Failed to archive chatbot", err);
    }
  };

  // Action: Soft-Delete Chatbot via DELETE API
  const handleDeleteBot = async (bot: typeof chatbots[0]) => {
    if (!workspaceId) return;
    if (!window.confirm(`Are you sure you want to delete "${bot.name}"?`)) return;

    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${bot.id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setChatbots((prev) => prev.filter((b) => b.id !== bot.id));
        showToast("Chatbot deleted");
      }
    } catch (err) {
      console.error("Failed to delete chatbot", err);
    }
  };

  return (
    <div className="space-y-5 max-w-5xl animate-fadeIn text-left mx-auto">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-[#0a1a2f] dark:text-white tracking-tight flex items-center gap-2.5">
            <Bot className="w-7 h-7 text-[#1a5cff] shrink-0" /> My Chatbots
          </h2>
          <p className="text-[#4a5a72] dark:text-slate-400 text-sm mt-1">
            {chatbots.length} active chatbots
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 p-1 bg-[#f7f7f7] dark:bg-slate-800 rounded-full border border-[#dee1e6] dark:border-white/10">
            {["All", "Active", "Draft", "Archived"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors cursor-pointer ${filter === f ? "bg-white dark:bg-slate-700 text-[#0a0b0d] dark:text-white shadow-sm" : "text-[#7c828a] dark:text-slate-400 hover:text-slate-200"}`}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            onClick={() => router.push(`/dashboard/${workspaceId}/bots/new`)}
            className="flex items-center gap-1.5 h-9 px-4 rounded-full bg-[#0a1a2f] dark:bg-blue-600 text-white text-xs font-bold hover:bg-[#142b47] dark:hover:bg-blue-700 transition-colors shadow-md border-0 cursor-pointer"
          >
            <Plus size={14} className="shrink-0" /> New Chatbot
          </button>
        </div>
      </div>

      {/* ── Bot Cards ── */}
      {chatbots.length > 0 ? (
        filtered.map((bot) => {
          const uiStatus = getUiStatus(bot);
          const docsCount = bot.docs || 0;
          const tone = "Professional";

          return (
            <div key={bot.id} className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 hover:border-[#1a5cff]/30 dark:hover:border-[#1a5cff]/30 transition-all p-5 group shadow-sm">
              <div className="flex items-start gap-4">
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 shadow-sm"
                  style={{ background: `linear-gradient(145deg, ${bot.color || "#0052ff"}, ${bot.color || "#0052ff"}cc)` }}
                >
                  <span className="text-xl leading-none">{bot.avatarEmoji || "🤖"}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    {editingBotId === bot.id ? (
                      <input
                        type="text"
                        value={editingBotName}
                        onChange={(e) => setEditingBotName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveRename(bot.id);
                          if (e.key === "Escape") setEditingBotId(null);
                        }}
                        onBlur={() => handleSaveRename(bot.id)}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        className="px-2.5 py-0.5 text-base font-bold border border-[#0052ff] rounded-lg bg-white dark:bg-[#0d111b] text-[#0a1a2f] dark:text-white outline-none"
                      />
                    ) : (
                      <p className="font-bold text-lg text-[#0a1a2f] dark:text-white">{bot.name}</p>
                    )}
                    <StatusBadge status={uiStatus} />
                  </div>
                  <p className="text-sm text-[#5b6f89] dark:text-slate-400 font-medium">
                    {bot.description || `${tone} tone · ${docsCount} ${docsCount === 1 ? 'document' : 'documents'}`}
                  </p>
                  <div className="flex items-center gap-5 mt-3 text-xs text-[#5b6f89] dark:text-slate-450 font-medium">
                    <span className="flex items-center gap-1.5">
                      <MessageSquare size={12} className="text-[#7b8fa8]" />
                      <span className="font-bold text-[#0a1a2f] dark:text-white">{bot.chats || 0}</span> conversations
                    </span>
                    {uiStatus === "Active" && (
                      <span className="flex items-center gap-1.5">
                        <Star size={12} className="text-[#7b8fa8]" />
                        <span className="font-bold text-[#0a1a2f] dark:text-white">98%</span> satisfaction
                      </span>
                    )}
                    <span className="flex items-center gap-1.5">
                      <Cpu size={12} className="text-[#7b8fa8]" />GPT-4o
                    </span>
                    <span className="flex items-center gap-1.5 ml-auto text-[#7b8fa8]">
                      <Clock size={12} />Edited {getUpdatedString(bot)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/dashboard/${workspaceId}/bots/${bot.id}/settings`); }}
                    className="h-8 px-3 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-bold text-[#5b616e] dark:text-slate-300 hover:bg-[#f7f7f7] dark:hover:bg-slate-800 flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Settings size={12} /> Edit
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/dashboard/${workspaceId}/bots/${bot.id}/playground`); }}
                    className="h-8 px-3 rounded-full bg-[#eef5ff] dark:bg-blue-900/30 text-[#1a5cff] dark:text-blue-400 text-xs font-bold hover:bg-[#dce9fe] dark:hover:bg-blue-900/50 flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <FlaskConical size={12} /> Test
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/dashboard/${workspaceId}/bots/${bot.id}/deployment`); }}
                    className="h-8 px-3 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-bold text-[#5b616e] dark:text-slate-300 hover:bg-[#f7f7f7] dark:hover:bg-slate-800 flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Rocket size={12} /> Deploy
                  </button>
                  <BotOverflowMenu
                    botName={bot.name}
                    onRename={() => {
                      setEditingBotId(bot.id);
                      setEditingBotName(bot.name);
                    }}
                    onArchive={() => handleArchiveBot(bot.id)}
                    onDelete={() => handleDeleteBot(bot)}
                  />
                </div>
              </div>
            </div>
          );
        })
      ) : (
        <div className="text-center py-16 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-3xl shadow-sm text-slate-400 dark:text-slate-500 space-y-3">
          <span className="text-3xl">🤖</span>
          <p className="text-sm font-bold">No chatbot assistants active in this workspace.</p>
        </div>
      )}

      {/* ── Create new button ── */}
      <button
        onClick={() => router.push(`/dashboard/${workspaceId}/bots/new`)}
        className="w-full py-5 border-2 border-dashed border-[#dee1e6] dark:border-white/10 rounded-2xl flex items-center justify-center gap-2 text-sm font-bold text-[#7c828a] dark:text-slate-400 hover:border-[#1a5cff]/40 hover:text-[#1a5cff] dark:hover:text-blue-400 transition-all cursor-pointer bg-transparent"
      >
        <Plus size={16} /> Create a new chatbot
      </button>
      
      {/* Subtle footer accent note */}
      <div className="mt-8 pt-6 border-t border-slate-100 dark:border-white/5 text-[10px] text-[#8b9fb8] dark:text-slate-500 text-center flex items-center justify-center gap-1.5 font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-[#1a5cff] shrink-0" />
        All chatbots are up to date
      </div>

      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
