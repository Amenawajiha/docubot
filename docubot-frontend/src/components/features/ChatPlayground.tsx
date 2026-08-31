"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Bot, Send, RefreshCw,
  Sparkles, Copy, Check, FileText,
  ThumbsUp, ThumbsDown
} from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";
import { usePlayground } from "@/hooks/usePlayground";
import { fetchApi } from "@/lib/api";

interface ChatMessage {
  role: "user" | "bot";
  text: string;
  time?: string;
}

interface ChatbotItem {
  id: string;
  name: string;
  status?: string;
  color?: string;
  selectedModel?: string;
  llmProvider?: string;
  tone?: string;
  systemPrompt?: string;
  welcomeMessage?: string;
}

interface DocumentItem {
  id: string;
  filename?: string;
  chunk_count?: number;
  upload_status?: string;
}

const MODELS = [
  { id: "gpt4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "claude35", name: "Claude 3.5 Sonnet", provider: "Anthropic" },
  { id: "gpt4omini", name: "GPT-4o Mini", provider: "OpenAI" },
  { id: "gemini15", name: "Gemini 1.5 Pro", provider: "Google" },
];

function FormattedMessage({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split("\n");
  const blocks: { type: "text" | "table"; content: string[] }[] = [];
  let currentBlock: { type: "text" | "table"; content: string[] } | null = null;

  for (const line of lines) {
    const isTableLine = line.trim().startsWith("|") && line.trim().endsWith("|");
    if (isTableLine) {
      if (currentBlock && currentBlock.type === "table") {
        currentBlock.content.push(line);
      } else {
        if (currentBlock) blocks.push(currentBlock);
        currentBlock = { type: "table", content: [line] };
      }
    } else {
      if (currentBlock && currentBlock.type === "text") {
        currentBlock.content.push(line);
      } else {
        if (currentBlock) blocks.push(currentBlock);
        currentBlock = { type: "text", content: [line] };
      }
    }
  }
  if (currentBlock) blocks.push(currentBlock);

  const renderFormattedLine = (line: string, idx: number) => {
    const isBullet = line.trim().startsWith("- ") || line.trim().startsWith("* ");
    const isNumbered = /^\d+\.\s/.test(line.trim());

    let content = line;
    if (isBullet) content = line.trim().substring(2);
    if (isNumbered) content = line.trim().replace(/^\d+\.\s/, "");

    const parts = content.split("**");
    const formattedContent = parts.map((part, partIdx) => {
      if (partIdx % 2 === 1) {
        return (
          <strong key={partIdx} className="font-semibold text-current">
            {part}
          </strong>
        );
      }
      return part;
    });

    if (isBullet) {
      return (
        <ul key={idx} className="list-disc pl-4 my-1">
          <li>{formattedContent}</li>
        </ul>
      );
    }

    if (isNumbered) {
      const num = line.trim().match(/^(\d+)\.\s/)?.[1] || "1";
      return (
        <ol key={idx} className="list-decimal pl-4 my-1" start={parseInt(num, 10)}>
          <li>{formattedContent}</li>
        </ol>
      );
    }

    return <p key={idx}>{formattedContent}</p>;
  };

  return (
    <div className="space-y-1.5 leading-relaxed">
      {blocks.map((block, blockIdx) => {
        if (block.type === "table") {
          const cleanRows = block.content
            .filter((l) => !/^\|[\s\-:|]+\|$/.test(l.trim()))
            .map((l) =>
              l
                .split("|")
                .slice(1, -1)
                .map((cell) => cell.trim())
            );

          if (cleanRows.length === 0) return null;

          const headerRow = cleanRows[0];
          const dataRows = cleanRows.slice(1);

          return (
            <div key={blockIdx} className="my-2 overflow-x-auto rounded-xl border border-slate-200 dark:border-white/10 shadow-sm">
              <table className="min-w-full text-left text-xs border-collapse divide-y divide-slate-200 dark:divide-white/10">
                <thead className="bg-slate-50 dark:bg-white/5 font-semibold text-[#0a0b0d] dark:text-white">
                  <tr>
                    {headerRow.map((h, hIdx) => (
                      <th key={hIdx} className="px-3 py-2 border-r border-slate-200 dark:border-white/10 last:border-r-0">
                        {renderFormattedLine(h, hIdx)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5 bg-white dark:bg-[#0d111b]">
                  {dataRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors">
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-2 border-r border-slate-100 dark:border-white/5 last:border-r-0 text-[#5b616e] dark:text-slate-300">
                          {renderFormattedLine(cell, cIdx)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        return (
          <div key={blockIdx} className="space-y-1">
            {block.content.map((l, lIdx) => renderFormattedLine(l, lIdx))}
          </div>
        );
      })}
    </div>
  );
}

export default function ChatPlayground() {
  const router = useRouter();
  const { currentChatbot, chatbots, workspaceId } = useWorkspace();

  const [userSelectedBot, setUserSelectedBot] = useState<ChatbotItem | null>(null);
  const activeBot = userSelectedBot || (currentChatbot as ChatbotItem | null) || (chatbots && (chatbots[0] as ChatbotItem)) || null;

  const activeBotId = activeBot?.id;

  const {
    messages: hookMessages,
    isTyping: loading,
    error,
    sendMessage: hookSendMessage,
    regenerateLastMessage,
  } = usePlayground(workspaceId, activeBotId);

  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState(activeBot?.selectedModel || MODELS[0].name);
  const [systemPrompt, setSystemPrompt] = useState(activeBot?.systemPrompt || "");
  const [copied, setCopied] = useState<number | null>(null);
  const [userSends, setUserSends] = useState(0);
  const [botDocuments, setBotDocuments] = useState<DocumentItem[]>([]);
  const [feedbackStatus, setFeedbackStatus] = useState<"up" | "down" | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const suggestedQuestions = [
    "How can I get started?",
    "What can you help me with?",
    "Tell me about pricing",
  ];

  // Update prompt & model when activeBot changes
  useEffect(() => {
    if (activeBot) {
      const prompt = activeBot.systemPrompt || "";
      const model = activeBot.selectedModel || MODELS[0].name;
      setTimeout(() => {
        setSystemPrompt(prompt);
        setSelectedModel(model);
      }, 0);
    }
  }, [activeBot]);

  // Fetch bot documents
  const fetchDocs = useCallback(async () => {
    await Promise.resolve();
    if (!activeBotId || !workspaceId) return;
    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${activeBotId}/documents`);
      if (res.ok) {
        const data: DocumentItem[] = await res.json();
        setTimeout(() => setBotDocuments(data), 0);
      }
    } catch (e) {
      console.error("Failed to fetch documents", e);
    }
  }, [activeBotId, workspaceId]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [hookMessages, loading]);

  const sendMessage = (text?: string) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    setUserSends((prev) => prev + 1);
    hookSendMessage(msg);
  };

  const clearChat = () => {
    setUserSends(0);
    window.location.reload();
  };

  const copyMessage = (i: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(i);
    setTimeout(() => setCopied(null), 1500);
  };

  const botColor = activeBot?.color || "#0052ff";
  const botName = activeBot?.name || "Support Assistant";

  // Build rendered messages combining initial welcome message with WebSocket stream
  const messages: ChatMessage[] = hookMessages.length > 0
    ? hookMessages.map((m) => ({
        role: m.sender === "user" ? "user" : "bot",
        text: m.text,
        time: m.time,
      }))
    : [
        {
          role: "bot",
          text: `👋 Hi! I'm ${botName}. How can I help you today?`,
        },
      ];

  return (
    <div className="flex h-[calc(100vh-140px)] min-h-0 bg-white dark:bg-[#030712] -m-4 sm:-m-6 lg:-m-6 xl:-m-8">
      {/* ── Left Sidebar Configuration ── */}
      <div className="w-64 shrink-0 border-r border-slate-200 dark:border-white/5 bg-white dark:bg-[#0d111b] flex flex-col">
        <div className="px-5 h-14 flex items-center border-b border-slate-200 dark:border-white/5">
          <p className="font-semibold text-sm text-[#0a0b0d] dark:text-white">Playground</p>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
          {/* Chatbot Selector List */}
          <div>
            <label className="block text-[10px] font-bold text-[#7c828a] uppercase tracking-wider mb-2">Chatbot</label>
            <div className="space-y-1">
              {chatbots && chatbots.map((b: ChatbotItem) => (
                <button
                  key={b.id}
                  onClick={() => {
                    setUserSelectedBot(b);
                    setUserSends(0);
                    router.push(`/dashboard/${workspaceId}/bots/${b.id}/playground`);
                  }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-left border-0 cursor-pointer transition-colors ${
                    activeBot?.id === b.id
                      ? "bg-[#f0f5ff] text-[#0052ff] dark:bg-blue-900/10 dark:text-blue-450"
                      : "hover:bg-[#f7f7f7] dark:hover:bg-white/5 text-[#5b616e] dark:text-slate-400 bg-transparent"
                  }`}
                >
                  <div className="w-4 h-4 rounded-full shrink-0" style={{ backgroundColor: b.color || "#0052ff" }} />
                  <span className="font-medium truncate">{b.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Model picker */}
          <div>
            <label className="block text-[10px] font-bold text-[#7c828a] uppercase tracking-wider mb-2">Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* System prompt override */}
          <div>
            <label className="block text-[10px] font-bold text-[#7c828a] uppercase tracking-wider mb-2">System Prompt</label>
            <textarea
              rows={4}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white placeholder-[#a8acb3] focus:border-[#0052ff] outline-none resize-none"
              placeholder="Override system prompt for testing…"
            />
          </div>

          {/* Trained Documents Sources Summary */}
          {botDocuments.length > 0 && (
            <div>
              <label className="block text-[10px] font-bold text-[#7c828a] uppercase tracking-wider mb-2">Trained Sources ({botDocuments.length})</label>
              <div className="space-y-1.5">
                {botDocuments.map((doc) => (
                  <div key={doc.id} className="p-2 rounded-lg bg-[#f7f7f7] dark:bg-white/5 text-[11px] flex items-center gap-1.5 truncate">
                    <FileText size={12} className="text-[#0052ff] shrink-0" />
                    <span className="truncate text-[#0a0b0d] dark:text-white">{doc.filename || "Source document"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Right Chat Panel ── */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#f7f7f7] dark:bg-[#030712]/50">
        {/* Header */}
        <div className="bg-white dark:bg-[#0d111b] border-b border-slate-200 dark:border-white/5 px-5 h-14 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-5 h-5 rounded-full shrink-0" style={{ backgroundColor: botColor }} />
            <span className="font-semibold text-sm text-[#0a0b0d] dark:text-white truncate">{botName}</span>
            <span className="text-xs text-[#7c828a] shrink-0">· Preview mode</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#e8f8f0] text-[#05b169] font-bold shrink-0">Live</span>
            <button onClick={clearChat} className="flex items-center gap-1 h-7 px-2.5 rounded-lg text-xs font-semibold text-[#7c828a] hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors border-0 bg-transparent cursor-pointer">
              <RefreshCw size={11} /> Reset
            </button>
          </div>
        </div>

        {/* Suggested Prompts */}
        {userSends === 0 && (
          <div className="px-6 py-3 flex items-center gap-2 border-b border-slate-200 dark:border-white/5 bg-[#f7f7f7] dark:bg-[#0d111b]/30 overflow-x-auto shrink-0">
            <Sparkles size={12} className="text-[#0052ff] shrink-0" />
            <span className="text-xs text-[#7c828a] shrink-0">Try:</span>
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="px-3 py-1 rounded-full border border-slate-200 dark:border-white/10 bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-400 hover:border-[#0052ff]/40 hover:text-[#0052ff] transition-all whitespace-nowrap border-0 cursor-pointer"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} gap-2.5`}>
              {msg.role === "bot" && (
                <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: botColor }}>
                  <Bot size={13} className="text-white" />
                </div>
              )}
              <div className="max-w-[75%] group relative">
                <div
                  className={`px-4 py-2.5 rounded-2xl text-xs leading-normal ${
                    msg.role === "user"
                      ? "text-white rounded-br-none shadow-sm"
                      : "bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white border border-slate-200 dark:border-white/5 rounded-bl-none shadow-sm"
                  }`}
                  style={msg.role === "user" ? { backgroundColor: botColor } : {}}
                >
                  <FormattedMessage text={msg.text} />
                </div>
                {msg.role === "bot" && (
                  <div className="flex items-center gap-1.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => copyMessage(i, msg.text)} className="w-5 h-5 rounded hover:bg-slate-200 dark:hover:bg-white/5 flex items-center justify-center border-0 bg-transparent cursor-pointer">
                      {copied === i ? <Check size={10} className="text-[#05b169]" /> : <Copy size={10} className="text-[#7c828a]" />}
                    </button>
                    <button onClick={() => setFeedbackStatus("up")} className={`w-5 h-5 rounded hover:bg-slate-200 dark:hover:bg-white/5 flex items-center justify-center border-0 bg-transparent cursor-pointer ${feedbackStatus === "up" ? "text-[#05b169]" : "text-[#7c828a]"}`}>
                      <ThumbsUp size={10} />
                    </button>
                    <button onClick={() => setFeedbackStatus("down")} className={`w-5 h-5 rounded hover:bg-slate-200 dark:hover:bg-white/5 flex items-center justify-center border-0 bg-transparent cursor-pointer ${feedbackStatus === "down" ? "text-rose-500" : "text-[#7c828a]"}`}>
                      <ThumbsDown size={10} />
                    </button>
                    <button onClick={regenerateLastMessage} className="text-[9.5px] font-semibold text-[#7c828a] hover:text-[#0052ff] border-0 bg-transparent cursor-pointer flex items-center gap-1">
                      <RefreshCw size={9} /> Regenerate
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-2.5 items-start">
              <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0" style={{ backgroundColor: botColor }}>
                <Bot size={13} className="text-white" />
              </div>
              <div className="bg-white dark:bg-[#0d111b] border border-slate-200 dark:border-white/5 rounded-2xl rounded-bl-none px-4 py-2.5 flex gap-1.5 items-center">
                {[0, 1, 2].map((j) => (
                  <span key={j} className="w-1.5 h-1.5 rounded-full bg-[#a8acb3] animate-bounce" style={{ animationDelay: `${j * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-xl text-center text-xs text-red-600 dark:text-red-400 animate-fadeIn">
              {error}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Message Input Form */}
        <div className="p-4 bg-white dark:bg-[#0d111b] border-t border-slate-200 dark:border-white/5 shrink-0">
          <div className="flex items-center gap-3 px-4 py-2.5 border border-slate-200 dark:border-white/10 rounded-full focus-within:border-[#0052ff] bg-white dark:bg-[#0d111b] transition-all">
            <input
              className="flex-1 text-xs text-[#0a0b0d] dark:text-white placeholder-[#a8acb3] outline-none bg-transparent"
              placeholder="Type a test message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0 transition-opacity disabled:opacity-40 border-0 cursor-pointer"
              style={{ backgroundColor: botColor }}
            >
              <Send size={11} />
            </button>
          </div>
          <p className="text-[10px] text-[#a8acb3] text-center mt-2">Playground uses live AI — responses may vary from production.</p>
        </div>
      </div>
    </div>
  );
}
