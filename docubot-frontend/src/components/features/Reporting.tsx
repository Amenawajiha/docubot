"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Download } from "lucide-react";
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { useWorkspace } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { CONV_DATA, SATISFACTION_DATA } from "@/components/ui/shared-dashboard";

interface AnalyticsSummary {
  total_sessions?: number;
  total_messages?: number;
  unique_users?: number;
  avg_confidence?: number;
  avg_response_time_ms?: number;
  total_tokens?: number;
  total_cost_usd?: number;
  clarification_rate?: number;
  resolution_rate?: number;
}

interface DailyMetric {
  date: string;
  total_sessions: number;
  total_messages: number;
  unique_users: number;
  avg_confidence?: number;
  resolution_rate?: number;
}

interface TopQuestionItem {
  content: string;
  count: number;
  avg_confidence?: number;
}

interface AnalyticsDashboard {
  summary?: AnalyticsSummary;
  daily_metrics?: DailyMetric[];
  top_questions?: TopQuestionItem[];
}

export default function Reporting() {
  const { workspaceId, currentChatbot } = useWorkspace();
  const [days, setDays] = useState<number>(7);
  const [analyticsData, setAnalyticsData] = useState<AnalyticsDashboard | null>(null);

  const defaultTopQuestions = [
    { q: "How do I reset my password?", count: 342, resolved: "98%" },
    { q: "What are your pricing plans?", count: 218, resolved: "94%" },
    { q: "How do I cancel my subscription?", count: 187, resolved: "91%" },
    { q: "Where is my invoice?", count: 156, resolved: "96%" },
    { q: "How do I contact support?", count: 134, resolved: "89%" },
  ];

  const fetchAnalytics = useCallback(async () => {
    if (!workspaceId) return;

    try {
      let url = `/workspaces/${workspaceId}/analytics?days=${days}`;
      if (currentChatbot?.id) {
        url += `&chatbot_id=${currentChatbot.id}`;
      }
      const res = await fetchApi(url);
      if (res.ok) {
        const data: AnalyticsDashboard = await res.json();
        setAnalyticsData(data);
      }
    } catch {
      // ponytail: backend /analytics API not implemented yet, fallback gracefully to mock analytics data
    }
  }, [workspaceId, currentChatbot, days]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Derived metrics
  const summary = analyticsData?.summary;

  const totalConvs = summary?.total_messages != null && summary.total_messages > 0
    ? summary.total_messages.toLocaleString()
    : "4,050";

  const resRate = summary?.resolution_rate != null
    ? `${(summary.resolution_rate * 100).toFixed(1)}%`
    : "89.3%";

  const avgSat = summary?.avg_confidence != null
    ? `${Math.round(summary.avg_confidence * 100)}%`
    : "91%";

  const escHuman = summary?.clarification_rate != null
    ? `${(summary.clarification_rate * 100).toFixed(1)}%`
    : "10.7%";

  // Derived daily conv chart data
  const chartConvData = (analyticsData?.daily_metrics && analyticsData.daily_metrics.length > 0)
    ? analyticsData.daily_metrics.map((dm) => {
        const d = new Date(dm.date);
        const dayName = d.toLocaleDateString("en-US", { weekday: "short" });
        return {
          day: dayName,
          conversations: dm.total_messages || dm.total_sessions || 0,
          resolved: Math.round((dm.total_messages || dm.total_sessions || 0) * (dm.resolution_rate || 0.9)),
        };
      })
    : CONV_DATA;

  // Derived top questions
  const displayQuestions = (analyticsData?.top_questions && analyticsData.top_questions.length > 0)
    ? analyticsData.top_questions.map((item) => ({
        q: item.content,
        count: item.count,
        resolved: item.avg_confidence != null ? `${Math.round(item.avg_confidence * 100)}%` : "95%",
      }))
    : defaultTopQuestions;

  const handleExport = () => {
    const csvRows = [
      ["Question", "Count", "Resolved"],
      ...displayQuestions.map((q) => [`"${q.q.replace(/"/g, '""')}"`, q.count, q.resolved]),
    ];
    const csvContent = "data:text/csv;charset=utf-8," + csvRows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `analytics_report_${days}d.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-5 max-w-6xl">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight">Reporting</h2>
          <p className="text-xs text-[#7c828a] mt-0.5">Analytics across all chatbots</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="h-8 px-3 border border-[#dee1e6] dark:border-white/10 rounded-full text-xs bg-white dark:bg-[#0d111b] text-[#5b616e] dark:text-slate-300 outline-none cursor-pointer"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={handleExport}
            className="h-8 px-3 rounded-full border border-[#dee1e6] dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-300 flex items-center gap-1.5 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors border-0 cursor-pointer"
          >
            <Download size={12} /> Export
          </button>
        </div>
      </div>

      {/* ── 4-col metrics ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Total Conversations", value: totalConvs, delta: "+12%" },
          { label: "Resolution Rate", value: resRate, delta: "+2.1%" },
          { label: "Avg. Satisfaction", value: avgSat, delta: "+3%" },
          { label: "Escalated to Human", value: escHuman, delta: "-2.1%" },
        ].map((k) => (
          <div key={k.label} className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-4">
            <p className="text-2xl font-bold font-mono text-[#0a0b0d] dark:text-white">{k.value}</p>
            <p className="text-xs text-[#7c828a] mt-0.5">{k.label}</p>
            <span className="text-xs font-semibold text-[#05b169] mt-2 block">{k.delta} vs last period</span>
          </div>
        ))}
      </div>

      {/* ── Charts ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5">
          <p className="font-semibold text-[#0a0b0d] dark:text-white text-sm mb-1">Daily Conversations</p>
          <p className="text-xs text-[#7c828a] mb-4">Conversations vs resolved</p>
          <div className="w-full h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartConvData} margin={{ left: -30, right: 0, top: 0, bottom: 0 }} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #dee1e6", fontSize: 12 }} />
                <Bar dataKey="conversations" fill="#0052ff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="resolved" fill="#05b169" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5">
          <p className="font-semibold text-[#0a0b0d] dark:text-white text-sm mb-1">Satisfaction Trend</p>
          <p className="text-xs text-[#7c828a] mb-4">Monthly CSAT score</p>
          <div className="w-full h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={SATISFACTION_DATA} margin={{ left: -30, right: 0, top: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#05b169" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#05b169" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <YAxis domain={[75, 100]} tick={{ fontSize: 11, fill: "#7c828a" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #dee1e6", fontSize: 12 }} />
                <Area type="monotone" dataKey="score" stroke="#05b169" strokeWidth={2} fill="url(#sg)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Top Questions ── */}
      <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 overflow-hidden">
        <div className="px-5 py-4 border-b border-[#dee1e6] dark:border-white/5">
          <p className="font-semibold text-[#0a0b0d] dark:text-white text-sm">Top Questions</p>
          <p className="text-xs text-[#7c828a]">Most frequently asked across all bots</p>
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-[#dee1e6] dark:border-white/5 bg-[#f7f7f7] dark:bg-white/3">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Question</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Count</th>
              <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Resolved</th>
            </tr>
          </thead>
          <tbody>
            {displayQuestions.map((q, i) => (
              <tr key={i} className={`${i < displayQuestions.length - 1 ? "border-b border-[#dee1e6] dark:border-white/5" : ""} hover:bg-[#f7f7f7] dark:hover:bg-white/3 transition-colors`}>
                <td className="px-5 py-3 text-sm text-[#0a0b0d] dark:text-white">{q.q}</td>
                <td className="px-4 py-3 text-sm font-mono font-semibold text-[#0a0b0d] dark:text-white">{q.count}</td>
                <td className="px-4 py-3"><span className="text-xs font-semibold text-[#05b169]">{q.resolved}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
