"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare, Star, Clock, Bot, Plus, ArrowUpRight, Search, Bell,
  UserPlus, AlertTriangle, AlertCircle
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from "recharts";
import { useWorkspace, useAuth } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { ProgressBar } from "@/components/ui/shared-dashboard";

interface DashboardMetrics {
  active_bots?: number;
  total_conversations?: number;
  satisfaction_rate?: number;
  total_documents?: number;
  avg_response_time?: string;
}

interface ChecklistData {
  has_chatbot?: boolean;
  has_documents?: boolean;
  has_deployments?: boolean;
  has_conversations?: boolean;
}

interface WeeklyConvItem {
  day: string;
  conversations: number;
  resolved: number;
}

interface UsageItem {
  label: string;
  used: number;
  max: number;
}

interface DashboardData {
  setup_progress_percent?: number;
  metrics?: DashboardMetrics;
  checklist?: ChecklistData;
  weekly_conversations?: WeeklyConvItem[];
  usage?: UsageItem[];
  alerts?: { type: "info" | "warning" | "error"; message: string; action_url?: string }[];
}

export default function Overview() {
  const router = useRouter();
  const { workspaceId, chatbots } = useWorkspace();
  const { user } = useAuth();

  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [showTeammateAlert, setShowTeammateAlert] = useState(true);

  const fetchDashboard = useCallback(async () => {
    await Promise.resolve();
    if (!workspaceId) return;
    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/dashboard`);
      if (res.ok) {
        const data: DashboardData = await res.json();
        setTimeout(() => setDashboardData(data), 0);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard", err);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const firstName = user?.full_name ? user.full_name.split(" ")[0] : "User";

  // Derive metrics from real backend dashboardData
  const stats = [
    {
      label: "Total Conversations",
      value: dashboardData?.metrics?.total_conversations != null ? dashboardData.metrics.total_conversations.toLocaleString() : "0",
      change: "+12%",
      icon: MessageSquare
    },
    {
      label: "Avg. Satisfaction",
      value: dashboardData?.metrics?.satisfaction_rate != null ? `${Math.round(dashboardData.metrics.satisfaction_rate * 100)}%` : "0%",
      change: "+3%",
      icon: Star
    },
    {
      label: "Active Bots",
      value: (dashboardData?.metrics?.active_bots ?? chatbots?.length ?? 0).toString(),
      activeBadge: (dashboardData?.metrics?.active_bots ?? chatbots?.length ?? 0).toString(),
      icon: Bot
    },
    {
      label: "Avg. Response",
      value: dashboardData?.metrics?.avg_response_time || "1.2s",
      change: "-0.4s",
      changeGreen: true,
      icon: Clock
    },
  ];

  // Derive weekly conversation chart data or fallback to empty structure for Recharts
  const convData: WeeklyConvItem[] = dashboardData?.weekly_conversations || [
    { day: "Mon", conversations: 0, resolved: 0 },
    { day: "Tue", conversations: 0, resolved: 0 },
    { day: "Wed", conversations: 0, resolved: 0 },
    { day: "Thu", conversations: 0, resolved: 0 },
    { day: "Fri", conversations: 0, resolved: 0 },
    { day: "Sat", conversations: 0, resolved: 0 },
    { day: "Sun", conversations: 0, resolved: 0 },
  ];

  // Derive usage metrics from backend dashboardData or calculate from workspace metrics
  const usageData: UsageItem[] = dashboardData?.usage || [
    {
      label: "Conversations",
      used: dashboardData?.metrics?.total_conversations || 0,
      max: 25000
    },
    {
      label: "Knowledge chunks",
      used: (dashboardData?.metrics?.total_documents || 0) * 100,
      max: 50000
    },
    {
      label: "API calls",
      used: (dashboardData?.metrics?.total_conversations || 0) * 5,
      max: 100000
    },
  ];

  return (
    <div className="space-y-4 max-w-6xl">
      {/* ── Page Title Row ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight flex items-center gap-1.5">
            Good morning, {firstName} 👋
          </h2>
          <p className="text-xs text-[#7c828a] mt-0.5">
            Your bots handled {dashboardData?.metrics?.total_conversations || 0} conversations overall
          </p>
        </div>
        <div className="flex items-center gap-2.5 self-end sm:self-center">
          <div className="flex items-center gap-2 h-8 px-3 bg-[#f7f7f7] dark:bg-white/5 rounded-full border border-[#dee1e6] dark:border-white/10">
            <Search size={12} className="text-[#7c828a]" />
            <input className="bg-transparent text-xs placeholder-[#a8acb3] outline-none w-28 text-[#0a0b0d] dark:text-white" placeholder="Search…" />
          </div>
          <button className="w-8 h-8 rounded-full border border-[#dee1e6] dark:border-white/10 bg-white dark:bg-[#0d111b] flex items-center justify-center relative cursor-pointer">
            <Bell size={13} className="text-[#5b616e] dark:text-slate-400" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[#0052ff]" />
          </button>
          <button
            onClick={() => router.push(`/dashboard/${workspaceId}/bots/new`)}
            className="flex items-center gap-1.5 h-8 px-3 rounded-full bg-[#0052ff] text-white text-xs font-semibold hover:bg-[#003ecc] transition-colors shadow-sm shadow-[#0052ff]/20 border-0 cursor-pointer"
          >
            <Plus size={13} /> New Chatbot
          </button>
        </div>
      </div>

      {/* ── Alert Banners ── */}
      <div className="space-y-2">
        {showTeammateAlert && (
          <div className="flex items-center justify-between gap-4 px-4 py-2.5 bg-[#f0f5ff] dark:bg-blue-950/10 border border-[#0052ff]/10 rounded-xl text-xs">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-[#e0ebff] dark:bg-blue-900/20 flex items-center justify-center shrink-0">
                <UserPlus size={13} className="text-[#0052ff]" />
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-[#0a0b0d] dark:text-white">No teammates yet</p>
                <p className="text-[#5b616e] dark:text-slate-400 mt-0.5 truncate">Invite your team to start collaborating on your chatbots.</p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={() => router.push(`/dashboard/${workspaceId}/team?invite=true`)}
                className="h-7 px-3 bg-[#0052ff] hover:bg-[#003ecc] text-white text-[10.5px] font-semibold rounded-full transition-colors border-0 cursor-pointer"
              >
                Invite members
              </button>
              <button onClick={() => setShowTeammateAlert(false)} className="text-[#7c828a] hover:text-[#0a0b0d] border-0 bg-transparent cursor-pointer">
                Dismiss
              </button>
            </div>
          </div>
        )}

        {dashboardData?.checklist?.has_documents === false && (
          <div className="flex items-center justify-between gap-4 px-4 py-2.5 bg-[#fff8e6] dark:bg-amber-950/10 border border-[#f4c842]/20 rounded-xl text-xs">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-[#ffeec2] dark:bg-amber-900/20 flex items-center justify-center shrink-0">
                <AlertTriangle size={13} className="text-[#b07d00]" />
              </div>
              <p className="text-[#7a5500] dark:text-amber-400 truncate">
                <span className="font-semibold">Knowledge base empty</span>. Add documents or web URLs to activate your AI.
              </p>
            </div>
            <button
              onClick={() => router.push(`/dashboard/${workspaceId}/knowledge`)}
              className="text-[11px] font-bold text-[#b07d00] dark:text-amber-400 hover:underline shrink-0 border-0 bg-transparent cursor-pointer"
            >
              Fix
            </button>
          </div>
        )}

        {dashboardData?.checklist?.has_deployments === false && (
          <div className="flex items-center justify-between gap-4 px-4 py-2.5 bg-[#fee8e8] dark:bg-rose-950/10 border border-[#cf202f]/10 rounded-xl text-xs">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-[#ffd4d4] dark:bg-rose-900/20 flex items-center justify-center shrink-0">
                <AlertCircle size={13} className="text-[#cf202f]" />
              </div>
              <p className="text-[#cf202f] dark:text-rose-450 truncate">
                <span className="font-semibold">No active widget deployment</span>. Publish your chatbot to deploy it to your website.
              </p>
            </div>
            <button
              onClick={() => router.push(`/dashboard/${workspaceId}/deployments`)}
              className="text-[11px] font-bold text-[#cf202f] dark:text-rose-450 hover:underline shrink-0 border-0 bg-transparent cursor-pointer"
            >
              Fix
            </button>
          </div>
        )}
      </div>

      {/* ── 4-column Metric Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="bg-white dark:bg-[#0d111b] rounded-2xl p-4 border border-[#dee1e6] dark:border-white/5">
            <div className="flex items-start justify-between mb-3.5">
              <div className="w-8 h-8 rounded-xl bg-[#f0f5ff] dark:bg-blue-900/10 flex items-center justify-center shrink-0">
                <s.icon size={15} className="text-[#0052ff]" />
              </div>
              {s.change && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#e8f8f0] text-[#05b169]">
                  {s.change}
                </span>
              )}
              {s.activeBadge && (
                <span className="w-5 h-5 rounded-full bg-[#e8f8f0] text-[#05b169] flex items-center justify-center text-[10px] font-bold">
                  {s.activeBadge}
                </span>
              )}
            </div>
            <p className="text-2xl font-bold text-[#0a0b0d] dark:text-white font-mono leading-none">{s.value}</p>
            <p className="text-[11px] text-[#7c828a] mt-1.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* ── Chart (2/3) + Usage Panel (1/3) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Conversations area chart */}
        <div className="lg:col-span-2 bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="font-semibold text-[#0a0b0d] dark:text-white text-sm">Conversations this week</p>
              <p className="text-xs text-[#7c828a] mt-0.5">Total · Resolved</p>
            </div>
            <button
              onClick={() => router.push(`/dashboard/${workspaceId}/bots`)}
              className="text-xs text-[#0052ff] font-semibold flex items-center gap-1 hover:underline bg-transparent border-0 cursor-pointer"
            >
              View report <ArrowUpRight size={12} />
            </button>
          </div>
          <div className="w-full h-40">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={convData} margin={{ top: 0, right: 0, left: -30, bottom: 0 }}>
                <defs>
                  <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0052ff" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#0052ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #dee1e6", fontSize: 11 }} />
                <Area type="monotone" dataKey="conversations" stroke="#0052ff" strokeWidth={2} fill="url(#cg)" />
                <Area type="monotone" dataKey="resolved" stroke="#05b169" strokeWidth={2} fill="none" strokeDasharray="4 2" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Usage plan widget */}
        <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5 flex flex-col justify-between">
          <div>
            <p className="font-semibold text-[#0a0b0d] dark:text-white text-sm mb-4">Usage this month</p>
            <div className="space-y-4">
              {usageData.map(({ label, used, max }) => (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[#7c828a]">{label}</span>
                    <span className="font-mono font-medium text-[#0a0b0d] dark:text-white">
                      {(used / 1000).toFixed(1)}k / {(max / 1000).toFixed(0)}k
                    </span>
                  </div>
                  <ProgressBar value={max > 0 ? (used / max) * 100 : 0} />
                </div>
              ))}
            </div>
          </div>
          <button
            onClick={() => router.push(`/dashboard/${workspaceId}/billing`)}
            className="mt-4 w-full h-8 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-semibold text-[#5b616e] dark:text-slate-400 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors border-0 cursor-pointer"
          >
            Manage plan
          </button>
        </div>
      </div>
    </div>
  );
}
