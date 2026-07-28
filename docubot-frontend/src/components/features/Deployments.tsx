"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Check, Copy, ExternalLink, Rocket, BookOpen,
  FileText, MessageSquare, Hash, Clock, RefreshCw,
  Activity, Package, UserCircle, ChevronDown
} from "lucide-react";
import { useAuth, useWorkspace } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { Toast } from "@/components/ui/shared-dashboard";

interface DeploymentState {
  status: "published" | "unpublished" | null;
  widgetChannel: string | null;
  embedScript: string | null;
  publishedAt: string | null;
  updatedAt: string | null;
}

interface ChatbotItem {
  id: string;
  name: string;
  status?: string;
  deployment_status?: string;
  color?: string;
  updated_at?: string;
  created_at?: string;
}

interface ChannelItem {
  id: string;
  channel_type: string;
  created_at?: string;
}

export default function Deployments() {
  const { user } = useAuth();
  const { workspaceId, currentChatbot, chatbots } = useWorkspace();

  const [userSelectedBot, setUserSelectedBot] = useState<ChatbotItem | null>(null);
  const activeBot = userSelectedBot || (currentChatbot as ChatbotItem | null) || (chatbots && (chatbots[0] as ChatbotItem)) || null;

  const [deployment, setDeployment] = useState<DeploymentState>({
    status: null,
    widgetChannel: null,
    embedScript: null,
    publishedAt: null,
    updatedAt: null,
  });
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState<"url" | "embed" | "chatbot-url" | null>(null);
  const [codeExpanded, setCodeExpanded] = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const [toastVisible, setToastVisible] = useState(false);
  const [notifyIds, setNotifyIds] = useState<string[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load deployment information (Chained 3-Step Waterfall per deploy_api_doc.md)
  const loadDeploymentInfo = useCallback(async () => {
    const botId = activeBot?.id;
    if (!workspaceId || !botId) return;

    try {
      // Step 1: Fetch chatbot details to verify status
      const botRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}`);
      if (!botRes.ok) return;
      const botData: ChatbotItem = await botRes.json();
      const isPublished = botData.deployment_status === "published" || botData.status === "Active";

      if (!isPublished) {
        setTimeout(() => {
          setDeployment({
            status: "unpublished",
            widgetChannel: null,
            embedScript: null,
            publishedAt: null,
            updatedAt: botData.updated_at || null,
          });
        }, 0);
        return;
      }

      // Step 2: Fetch channels
      const chanRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}/channels`);
      let channelId: string | null = null;
      let embedScript: string | null = null;

      if (chanRes.ok) {
        const channels: ChannelItem[] = await chanRes.json();
        const widgetChannel = channels.find((c) => c.channel_type === "widget") || channels[0];

        if (widgetChannel) {
          channelId = widgetChannel.id;

          // Step 3: Fetch embed snippet for widget channel
          const embedRes = await fetchApi(
            `/workspaces/${workspaceId}/chatbots/${botId}/channels/${channelId}/embed`
          );
          if (embedRes.ok) {
            const embedData = await embedRes.json();
            embedScript = embedData.embed_script || null;
          }
        }
      }

      setTimeout(() => {
        setDeployment({
          status: "published",
          widgetChannel: channelId,
          embedScript: embedScript,
          publishedAt: botData.updated_at || botData.created_at || null,
          updatedAt: botData.updated_at || null,
        });
      }, 0);
    } catch (err) {
      console.error("Failed to fetch deployment info", err);
    }
  }, [workspaceId, activeBot?.id]);

  useEffect(() => {
    loadDeploymentInfo();
  }, [loadDeploymentInfo]);

  // Click outside listener for dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2500);
  };

  const copyText = (text: string, key: "url" | "embed" | "chatbot-url") => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      showToast(
        key === "url" || key === "chatbot-url"
          ? "URL copied to clipboard"
          : "Embed code copied to clipboard"
      );
      setTimeout(() => setCopiedKey(null), 2000);
    });
  };

  const isLive = deployment.status === "published" || activeBot?.status === "Active";

  const handleTogglePublish = async () => {
    const botId = activeBot?.id;
    const nextState = !isLive;

    if (workspaceId && botId) {
      if (nextState) {
        // Prevent publishing if the knowledge base is completely empty
        try {
          const docsRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}/documents`);
          if (docsRes.ok) {
            const docs = await docsRes.json();
            if (!docs || docs.length === 0) {
              showToast("Cannot publish: Knowledge base is empty. Please add documents first.");
              return;
            }
          }
        } catch (err) {
          console.error("Failed to validate knowledge base", err);
          showToast("Failed to validate knowledge base.");
          return;
        }
      }

      try {
        if (nextState) {
          await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}`, {
            method: "PATCH",
            body: JSON.stringify({
              status: "Active",
              deployment_status: "published",
            }),
          });
        } else {
          await fetchApi(`/workspaces/${workspaceId}/chatbots/${botId}`, {
            method: "DELETE",
          });
        }
      } catch (err) {
        console.error("Failed to update bot deployment status", err);
        showToast("Failed to update deployment status.");
        return;
      }
    }

    if (activeBot) {
      setUserSelectedBot({
        ...activeBot,
        status: nextState ? "Active" : "Inactive",
        deployment_status: nextState ? "published" : "archived",
      });
    }
    setDeployment((prev) => ({
      ...prev,
      status: nextState ? "published" : "unpublished",
    }));
    showToast(nextState ? "Bot published successfully" : "Bot unpublished");
    loadDeploymentInfo();
  };

  const currentBotId = activeBot?.id;
  const botName = activeBot?.name || "Support Assistant";
  const botColor = activeBot?.color || "#0052ff";
  const botSlug = botName.toLowerCase().replace(/\s+/g, "-");
  const publicUrl = `https://chat.docubot.ai/${botSlug}`;

  const generatedEmbed = deployment.widgetChannel
    ? `<script\n  src="http://localhost:3000/widget.js"\n  data-chatbot-id="${currentBotId || ""}"\n  data-workspace="${workspaceId || ""}"\n  data-channel-id="${deployment.widgetChannel}"\n  async\n></script>`
    : `<!-- No web channel configured yet. Please configure a channel to get the embed code. -->`;
  const embedCode = deployment.embedScript || generatedEmbed;

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Recently";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return dateStr;
    }
  };

  const details = [
    { label: "Deployment Method", value: "Website Widget", icon: Package },
    { label: "Published By", value: user?.full_name || "Workspace Admin", icon: UserCircle },
    { label: "Published", value: formatDate(deployment.publishedAt), icon: Clock },
    { label: "Last Updated", value: formatDate(deployment.updatedAt), icon: RefreshCw },
    { label: "Deployment Status", value: isLive ? "Live" : "Unpublished", icon: Activity },
  ];

  return (
    <div className="space-y-6 max-w-4xl">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight">Deployment</h2>
          <p className="text-xs text-[#7c828a] mt-0.5">Publish, verify status, and integrate your chatbot</p>
        </div>

        {/* Right side selector & action buttons */}
        <div className="flex items-center gap-2">
          {/* Chatbot Dropdown Selector */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 px-3 h-8 border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] rounded-xl text-xs font-semibold text-[#0a0b0d] dark:text-white hover:bg-slate-50 dark:hover:bg-white/5 transition-colors select-none cursor-pointer"
            >
              <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: botColor }} />
              <span className="truncate max-w-[120px]">{botName}</span>
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ${isLive ? "bg-[#e8f8f0] text-[#05b169]" : "bg-[#fff8e6] text-[#b07d00]"}`}>
                {isLive ? "Active" : "Draft"}
              </span>
              <ChevronDown size={11} className="text-slate-400 shrink-0" />
            </button>

            {dropdownOpen && chatbots && chatbots.length > 0 && (
              <div className="absolute right-0 top-full mt-1 w-52 bg-white dark:bg-[#0d111b] border border-slate-200 dark:border-white/10 rounded-xl shadow-lg py-1.5 z-50">
                {chatbots.map((b: ChatbotItem) => (
                  <button
                    key={b.id}
                    onClick={() => {
                      setUserSelectedBot(b);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs hover:bg-[#f7f7f7] dark:hover:bg-white/5 flex items-center justify-between border-0 bg-transparent cursor-pointer ${
                      activeBot?.id === b.id ? "font-semibold text-[#0052ff]" : "text-slate-700 dark:text-slate-350"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: b.color || "#0052ff" }} />
                      <span className="truncate">{b.name}</span>
                    </div>
                    <span className={`text-[9px] px-1 rounded font-bold ${b.status === "Active" ? "bg-[#e8f8f0] text-[#05b169]" : "bg-slate-100 text-[#7c828a]"}`}>
                      {b.status === "Active" ? "Active" : "Draft"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleTogglePublish}
            className="h-8 px-3.5 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-350 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors cursor-pointer"
          >
            {isLive ? "Unpublish" : "Publish"}
          </button>
        </div>
      </div>

      {/* 1. Live Status Banner */}
      <section className={`rounded-2xl border p-5 transition-colors ${isLive ? "bg-[#e8f8f0] dark:bg-[#e8f8f0]/10 border-[#05b169]/30" : "bg-white dark:bg-[#0d111b] border-dashed border-slate-200 dark:border-white/10"}`}>
        <div className="flex flex-col sm:flex-row sm:items-start gap-4">
          <div className={`w-11 h-11 rounded-full flex items-center justify-center shrink-0 ${isLive ? "bg-[#05b169]" : "bg-slate-100 dark:bg-white/5"}`}>
            {isLive ? <Check size={20} className="text-white" strokeWidth={2.5} /> : <Rocket size={20} className="text-[#a8acb3]" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">{isLive ? `${botName} is live` : `${botName} is not published`}</h3>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold ${isLive ? "bg-[#e8f8f0] text-[#05b169]" : "bg-[#f7f7f7] text-[#7c828a]"}`}>
                {isLive && <span className="w-1.5 h-1.5 rounded-full bg-[#05b169] animate-pulse" />}
                {isLive ? "Live" : "Draft"}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#eef0f3] dark:bg-white/10 text-[#5b616e] dark:text-slate-350 uppercase">PRODUCTION</span>
            </div>
            {isLive ? (
              <p className="text-xs text-[#5b616e] dark:text-slate-450 mb-3">Version <span className="font-mono font-semibold text-[#0a0b0d] dark:text-white">v1.2.3</span> · Published {formatDate(deployment.publishedAt)}</p>
            ) : (
              <p className="text-xs text-[#7c828a] mb-3">Publish to make your chatbot available and generate integration assets.</p>
            )}
            <div className="flex flex-wrap gap-2">
              <a
                href={publicUrl}
                target="_blank"
                rel="noreferrer"
                className={`h-8 px-4 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white text-xs font-semibold transition-colors flex items-center gap-1.5 ${!isLive && "pointer-events-none opacity-40"}`}
              >
                <ExternalLink size={12} /> Open Chat
              </a>
              <button
                onClick={() => copyText(publicUrl, "url")}
                disabled={!isLive}
                className="h-8 px-4 rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-350 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors flex items-center gap-1.5 disabled:opacity-40 cursor-pointer"
              >
                {copiedKey === "url" ? <Check size={12} className="text-[#05b169]" /> : <Copy size={12} />}
                {copiedKey === "url" ? "Copied" : "Copy URL"}
              </button>
              <button
                onClick={handleTogglePublish}
                className="h-8 px-4 rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-350 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Rocket size={12} className="text-slate-400" />
                {isLive ? "Unpublish" : "Publish"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Integration */}
      <section className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-white/5">
          <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Integration</p>
          <p className="text-xs text-[#7c828a] mt-0.5">Share your public URL or embed the website widget</p>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">Chatbot URL</label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input readOnly value={publicUrl} className="flex-1 h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900/50 text-[#7c828a] font-mono focus:outline-none" />
              <div className="flex gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => copyText(publicUrl, "chatbot-url")}
                  className="h-9 px-3.5 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors flex items-center gap-1.5 text-xs font-semibold text-[#5b616e] dark:text-slate-350 bg-white dark:bg-[#0d111b] cursor-pointer"
                >
                  {copiedKey === "chatbot-url" ? <Check size={11} className="text-[#05b169]" /> : <Copy size={11} />}
                  <span>{copiedKey === "chatbot-url" ? "Copied" : "Copy"}</span>
                </button>
                <a
                  href={publicUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="h-9 px-3.5 rounded-xl border border-slate-200 dark:border-white/10 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors flex items-center justify-center gap-1.5 text-xs font-semibold text-[#5b616e] dark:text-slate-350 bg-white dark:bg-[#0d111b]"
                >
                  <ExternalLink size={11} /> Open
                </a>
              </div>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-[#5b616e]">Website Embed Code</label>
              <button
                type="button"
                onClick={() => setCodeExpanded(e => !e)}
                className="text-xs font-semibold text-[#0052ff] hover:underline border-0 bg-transparent cursor-pointer"
              >
                {codeExpanded ? "Collapse" : "Expand"}
              </button>
            </div>
            <p className="text-[10.5px] text-[#7c828a] mb-2.5">Paste this script immediately before the closing <code className="font-mono text-[#cf202f] bg-slate-100 dark:bg-white/5 px-1 py-0.5 rounded">&lt;/body&gt;</code> tag.</p>
            <div className="relative">
              <pre className={`bg-[#0a0b0d] rounded-xl p-4 pr-28 text-xs text-[#05b169] font-mono leading-relaxed ${codeExpanded ? "whitespace-pre-wrap break-all" : "whitespace-pre overflow-hidden max-h-24"}`}>
                {embedCode}
              </pre>
              <button
                type="button"
                onClick={() => copyText(embedCode, "embed")}
                className="absolute top-3 right-3 h-7 px-3 rounded-full bg-white/15 hover:bg-white/20 text-white text-[11px] font-semibold flex items-center gap-1.5 transition-colors border-0 cursor-pointer"
              >
                {copiedKey === "embed" ? <><Check size={11} className="text-[#05b169]" /> Copied</> : <><Copy size={11} /> Copy Code</>}
              </button>
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3">
              <a href="#" onClick={(e) => { e.preventDefault(); alert("Opening installation guide..."); }} className="text-xs font-semibold text-[#0052ff] hover:underline inline-flex items-center gap-1.5"><BookOpen size={12} /> View Installation Guide</a>
              <a href="#" onClick={(e) => { e.preventDefault(); alert("Opening API documentation..."); }} className="text-xs font-semibold text-[#0052ff] hover:underline inline-flex items-center gap-1.5"><FileText size={12} /> View API Documentation</a>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Deployment Details */}
      <section className="bg-[#ffffff] dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-white/5 bg-[#f7f7f7] dark:bg-white/3">
          <p className="text-xs font-bold text-[#0a0b0d] dark:text-white">Deployment Details</p>
          <p className="text-[10px] text-[#7c828a] mt-0.5">Current production release information</p>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-white/5">
          {details.map(row => (
            <div key={row.label} className="flex items-center gap-3 px-5 py-3.5 hover:bg-[#f7f7f7]/30 transition-colors">
              <div className="w-8 h-8 rounded-lg bg-[#f7f7f7] dark:bg-white/5 flex items-center justify-center shrink-0">
                <row.icon size={13} className="text-[#7c828a]" />
              </div>
              <span className="text-xs font-semibold text-[#7c828a] w-36 shrink-0">{row.label}</span>
              <span className={`text-xs font-semibold flex-1 ${row.label === "Deployment Status" && isLive ? "text-[#05b169]" : "text-[#0a0b0d] dark:text-white"}`}>{row.value}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Future Channels */}
      <section className="space-y-3">
        <div>
          <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white">More Deployment Channels</p>
          <p className="text-xs text-[#7c828a] mt-0.5">Additional deployment options will be available in future releases.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { id: "whatsapp", name: "WhatsApp", icon: MessageSquare },
            { id: "slack", name: "Slack", icon: Hash },
          ].map(ch => {
            const notified = notifyIds.includes(ch.id);
            return (
              <div key={ch.id} className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 p-4 flex items-center gap-3 shadow-sm">
                <div className="w-9 h-9 rounded-xl bg-[#f7f7f7] dark:bg-white/5 flex items-center justify-center shrink-0">
                  <ch.icon size={15} className="text-[#7c828a]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-xs font-semibold text-[#0a0b0d] dark:text-white">{ch.name}</p>
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#eef0f3] dark:bg-white/10 text-[#7c828a] uppercase tracking-wide">Coming Soon</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (notified) return;
                      setNotifyIds(prev => [...prev, ch.id]);
                      showToast(`We'll notify you when ${ch.name} is available`);
                    }}
                    className={`mt-1.5 text-xs font-semibold transition-colors border-0 bg-transparent cursor-pointer ${notified ? "text-[#05b169]" : "text-[#0052ff] hover:underline"}`}
                  >
                    {notified ? "You're on the list" : "Notify Me"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
