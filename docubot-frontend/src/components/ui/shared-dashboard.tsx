"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  CheckCircle2, XCircle, RefreshCw, MoreHorizontal,
  Edit3, Package, Trash2, Sparkles, Check,
} from "lucide-react";

/* ─── Types ─── */
export interface ChatBot {
  id: string;
  name: string;
  description: string;
  status: "active" | "draft" | "indexing" | "Active" | "Inactive";
  conversations: number;
  satisfaction: number;
  lastEdited: string;
  model: string;
  color: string;
}

/* ─── Mock data ─── */
export const MODELS = [
  { id: "gpt4o", name: "GPT-4o", provider: "OpenAI", speed: 92, quality: 96, cost: 38, context: "128K", badge: "Recommended", useCase: "Complex reasoning & analysis" },
  { id: "claude35", name: "Claude 3.5 Sonnet", provider: "Anthropic", speed: 88, quality: 94, cost: 42, context: "200K", badge: "Best for docs", useCase: "Long documents & nuance" },
  { id: "gpt4omini", name: "GPT-4o Mini", provider: "OpenAI", speed: 99, quality: 79, cost: 8, context: "128K", badge: "Fastest", useCase: "High-volume, simple queries" },
  { id: "gemini15", name: "Gemini 1.5 Pro", provider: "Google", speed: 85, quality: 91, cost: 35, context: "1M", badge: "Largest context", useCase: "Massive knowledge bases" },
];

export const CONV_DATA = [
  { day: "Mon", conversations: 320, resolved: 290 },
  { day: "Tue", conversations: 480, resolved: 430 },
  { day: "Wed", conversations: 410, resolved: 380 },
  { day: "Thu", conversations: 620, resolved: 570 },
  { day: "Fri", conversations: 590, resolved: 530 },
  { day: "Sat", conversations: 280, resolved: 260 },
  { day: "Sun", conversations: 190, resolved: 180 },
];

export const SATISFACTION_DATA = [
  { month: "Jan", score: 82 }, { month: "Feb", score: 85 },
  { month: "Mar", score: 87 }, { month: "Apr", score: 84 },
  { month: "May", score: 89 }, { month: "Jun", score: 91 },
  { month: "Jul", score: 94 },
];

export const DOCS = [
  { id: "1", name: "Product Manual Q4 2024.pdf", size: "4.2 MB", chunks: 847, status: "indexed", uploaded: "2h ago", type: "pdf" },
  { id: "2", name: "Support FAQ.docx", size: "1.1 MB", chunks: 312, status: "indexed", uploaded: "1d ago", type: "docx" },
  { id: "3", name: "Pricing Tiers.csv", size: "48 KB", chunks: 64, status: "indexed", uploaded: "2d ago", type: "csv" },
  { id: "4", name: "Onboarding Guide.txt", size: "220 KB", chunks: 128, status: "indexing", uploaded: "5m ago", type: "txt" },
  { id: "5", name: "API Reference.pdf", size: "8.9 MB", chunks: 0, status: "failed", uploaded: "1h ago", type: "pdf" },
];

export const TONES = [
  { id: "professional", emoji: "👔", label: "Professional", desc: "Formal & authoritative" },
  { id: "friendly",     emoji: "😊", label: "Friendly",     desc: "Warm & approachable" },
  { id: "casual",       emoji: "👋", label: "Casual",       desc: "Relaxed & conversational" },
  { id: "empathetic",   emoji: "🤝", label: "Empathetic",   desc: "Caring & supportive" },
  { id: "concise",      emoji: "⚡", label: "Concise",      desc: "Brief & to the point" },
  { id: "playful",      emoji: "🎉", label: "Playful",      desc: "Fun & energetic" },
];

export const TONE_DESCRIPTIONS: Record<string, string> = {
  professional: "Your bot will use formal language, maintain a respectful distance, and prioritise accuracy over warmth.",
  friendly:     "Your bot will greet users warmly, use positive language, and feel like a helpful colleague.",
  casual:       "Your bot will feel like a chat with a knowledgeable friend — relaxed, natural, and jargon-free.",
  empathetic:   "Your bot will acknowledge user feelings first, then provide clear and compassionate guidance.",
  concise:      "Your bot will give direct, short answers. No filler, no fluff — just the answer.",
  playful:      "Your bot will use light humour, emoji, and an upbeat tone to keep interactions fun.",
};

/* ─── Status Badge ─── */
export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    active:   { label: "Active",   cls: "bg-[#e8f8f0] text-[#05b169]" },
    Active:   { label: "Active",   cls: "bg-[#e8f8f0] text-[#05b169]" },
    draft:    { label: "Draft",    cls: "bg-[#f7f7f7] text-[#7c828a]" },
    Draft:    { label: "Draft",    cls: "bg-[#f7f7f7] text-[#7c828a]" },
    archived: { label: "Archived", cls: "bg-[#fee8e8] text-[#cf202f]" },
    Archived: { label: "Archived", cls: "bg-[#fee8e8] text-[#cf202f]" },
    Inactive: { label: "Archived", cls: "bg-[#fee8e8] text-[#cf202f]" },
    inactive: { label: "Archived", cls: "bg-[#fee8e8] text-[#cf202f]" },
    indexing: { label: "Indexing", cls: "bg-[#fff8e6] text-[#b07d00]" },
  };
  const { label, cls } = map[status] ?? { label: status, cls: "bg-[#f7f7f7] text-[#7c828a]" };
  const isActive = status === "active" || status === "Active";
  const isArchived = status === "archived" || status === "Archived" || status === "Inactive" || status === "inactive";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {isActive && <span className="w-1.5 h-1.5 rounded-full bg-[#05b169]" />}
      {isArchived && <span className="w-1.5 h-1.5 rounded-full bg-[#cf202f]" />}
      {label}
    </span>
  );
}

/* ─── Doc Status Badge ─── */
export function DocStatusBadge({ status }: { status: string }) {
  if (status === "indexed" || status === "Ready") return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#e8f8f0] text-[#05b169]"><CheckCircle2 size={10} />Indexed</span>;
  if (status === "indexing" || status === "Syncing") return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#fff8e6] text-[#b07d00]"><RefreshCw size={10} className="animate-spin" />Indexing</span>;
  return <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#fee8e8] text-[#cf202f]"><XCircle size={10} />Failed</span>;
}

/* ─── Progress Bar ─── */
export function ProgressBar({ value, color = "#0052ff" }: { value: number; color?: string }) {
  return (
    <div className="w-full h-1.5 bg-[#eef0f3] rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.max(0, Math.min(100, value))}%`, backgroundColor: color }} />
    </div>
  );
}

/* ─── Metric Bar ─── */
export function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-[#7c828a] w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[#eef0f3] rounded-full overflow-hidden">
        <div className="h-full rounded-full bg-[#0052ff]" style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-mono font-medium text-[#0a0b0d] w-8 text-right">{value}</span>
    </div>
  );
}

/* ─── Toast ─── */
export function Toast({ message, visible }: { message: string; visible: boolean }) {
  return (
    <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5 px-4 py-2.5 bg-[#0a0b0d] text-white rounded-full text-sm font-medium shadow-lg transition-all duration-300 pointer-events-none ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"}`}>
      <CheckCircle2 size={14} className="text-[#05b169] shrink-0" />
      {message}
    </div>
  );
}

/* ─── Bot Overflow Menu ─── */
export function BotOverflowMenu({
  botName,
  compact = false,
  onRename,
  onArchive,
  onDelete,
}: {
  botName: string;
  compact?: boolean;
  onRename?: () => void;
  onArchive?: () => void;
  onDelete?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const items = [
    { id: "rename", label: "Rename", icon: Edit3, action: onRename },
    { id: "archive", label: "Archive", icon: Package, action: onArchive },
    { id: "delete", label: "Delete", icon: Trash2, danger: true, action: onDelete },
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={`More actions for ${botName}`}
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}
        className={compact
          ? "w-7 h-7 rounded-full border border-[#dee1e6] flex items-center justify-center hover:bg-[#f7f7f7] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0052ff]"
          : "w-8 h-8 rounded-full border border-[#dee1e6] flex items-center justify-center hover:bg-[#f7f7f7] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0052ff]"
        }
      >
        <MoreHorizontal size={compact ? 13 : 14} className="text-[#7c828a]" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-44 bg-white dark:bg-[#0d111b] rounded-xl border border-[#dee1e6] dark:border-white/10 shadow-xl z-50 py-1 overflow-hidden">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                if (item.action) item.action();
              }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-xs font-semibold transition-colors border-0 bg-transparent cursor-pointer ${
                item.danger
                  ? "text-[#cf202f] hover:bg-[#fee8e8] dark:hover:bg-rose-950/20"
                  : "text-[#5b616e] dark:text-slate-300 hover:bg-[#f7f7f7] dark:hover:bg-white/5 hover:text-[#0a0b0d]"
              }`}
            >
              <item.icon size={13} className="shrink-0" />
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Tone Selector ─── */
export function ToneSelector({ value, onChange }: { value: string; onChange: (t: string) => void }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-[#0a0b0d] mb-1">Tone of Voice</label>
      <p className="text-xs text-[#7c828a] mb-3">How should your chatbot communicate with users?</p>
      <div className="grid grid-cols-3 gap-2">
        {TONES.map((t) => {
          const selected = value === t.id;
          return (
            <button key={t.id} onClick={() => onChange(t.id)}
              className={`flex flex-col items-start gap-1 p-3 rounded-xl border text-left transition-all ${selected ? "border-[#0052ff] bg-[#f0f5ff]" : "border-[#dee1e6] bg-white hover:border-[#0052ff]/40"}`}>
              <div className="flex items-center justify-between w-full">
                <span className="text-lg leading-none">{t.emoji}</span>
                {selected && <div className="w-4 h-4 rounded-full bg-[#0052ff] flex items-center justify-center"><Check size={9} className="text-white" /></div>}
              </div>
              <p className={`text-xs font-semibold mt-1 ${selected ? "text-[#0052ff]" : "text-[#0a0b0d]"}`}>{t.label}</p>
              <p className="text-[10px] text-[#7c828a] leading-tight">{t.desc}</p>
            </button>
          );
        })}
      </div>
      {value && (
        <div className="mt-3 px-3 py-2.5 rounded-xl bg-[#f7f7f7] border border-[#dee1e6] flex items-start gap-2">
          <Sparkles size={13} className="text-[#0052ff] shrink-0 mt-0.5" />
          <p className="text-xs text-[#5b616e]">{TONE_DESCRIPTIONS[value]}</p>
        </div>
      )}
    </div>
  );
}
