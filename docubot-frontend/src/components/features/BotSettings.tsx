"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  Zap,
  MessageCircle,
  Brain,
  Send,
  Bot,
  Smile,
  Briefcase,
  Sparkles,
  Terminal,
  Cpu,
  Globe,
  Settings,
  Palette,
  MessageSquare
} from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";
import { usePlayground } from "@/hooks/usePlayground";
import { fetchApi } from "@/lib/api";

const TONE_ICONS: Record<string, React.ComponentType<any>> = {
  Friendly: Smile,
  Professional: Briefcase,
  Playful: Sparkles,
  Technical: Terminal,
};

const MODEL_ICONS: Record<string, React.ComponentType<any>> = {
  "gpt-4o": Zap,
  "gpt-4-turbo": Brain,
  "llama-3-70b": Terminal,
  "mixtral-8x7b": Cpu,
};

const PROVIDER_MODELS: Record<string, string[]> = {
  OpenAI: ["gpt-4o", "gpt-4-turbo"],
  Groq: ["openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
};

export default function BotSettings() {
  const router = useRouter();
  const [botStudioTab, setBotStudioTab] = useState<"ai-engine" | "appearance" | "language" | "preview">("preview");

  const {
    chatbots,
    setChatbots,
    currentChatbot,
    workspaceId
  } = useWorkspace();

  const {
    messages: studioMessages,
    isTyping: studioIsTyping,
    connectionStatus,
    error,
    sendMessage
  } = usePlayground(workspaceId || undefined, currentChatbot?.id);

  const [studioInput, setStudioInput] = useState("");

  const handleSendStudioMessage = (e?: React.FormEvent, textOverride?: string) => {
    if (e) e.preventDefault();
    const query = textOverride || studioInput;
    if (query.trim()) {
      sendMessage(query);
      setStudioInput("");
    }
  };

  // Local draft states for configuration
  const [name, setName] = useState("");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [avatarEmoji, setAvatarEmoji] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [llmProvider, setLlmProvider] = useState("OpenAI");
  const [selectedModel, setSelectedModel] = useState("gpt-4o");
  const [apiKey, setApiKey] = useState("");
  const [color, setColor] = useState("#0052ff");
  const [tone, setTone] = useState("Friendly");

  // Sync draft states when currentChatbot loads or changes
  useEffect(() => {
    if (currentChatbot) {
      setName(currentChatbot.name || "");
      setWelcomeMessage(currentChatbot.welcomeMessage || "Hello! Welcome to our website. How can I help you today?");
      setAvatarEmoji(currentChatbot.avatarEmoji || "🤖");
      setSystemPrompt(currentChatbot.systemPrompt || "You are a helpful assistant...");
      setLlmProvider(currentChatbot.llmProvider || "OpenAI");
      setSelectedModel(currentChatbot.selectedModel || "gpt-4o");
      setApiKey(currentChatbot.apiKey || "");
      setColor(currentChatbot.color || "#0052ff");
      setTone(currentChatbot.tone || "Friendly");
    }
  }, [currentChatbot]);

  const handleSaveSettings = async () => {
    if (botStudioTab === "ai-engine") {
      try {
        const payload = {
          llm_provider: llmProvider.toLowerCase(),
          llm_model: selectedModel,
          custom_api_key: apiKey || null,
          custom_system_prompt: systemPrompt,
          tone_preset: tone.toLowerCase()
        };
        const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Failed to save AI Engine settings");
        
        const updatedBot = await res.json();
        
        setChatbots((prev) =>
          prev.map((b) =>
            b.id === currentChatbot.id
              ? {
                  ...b,
                  systemPrompt: updatedBot.custom_system_prompt,
                  llmProvider: updatedBot.llm_provider ? (updatedBot.llm_provider.toLowerCase() === "openai" ? "OpenAI" : updatedBot.llm_provider.charAt(0).toUpperCase() + updatedBot.llm_provider.slice(1).toLowerCase()) : "OpenAI",
                  selectedModel: updatedBot.llm_model,
                  tone: updatedBot.tone_preset ? updatedBot.tone_preset.charAt(0).toUpperCase() + updatedBot.tone_preset.slice(1).toLowerCase() : "Friendly",
                  apiKey: apiKey
                }
              : b
          )
        );
        alert("AI Engine settings saved successfully!");
      } catch (err) {
        console.error(err);
        alert("Error saving settings");
      }
    } else {
      setChatbots((prev) =>
        prev.map((b) =>
          b.id === currentChatbot.id
            ? {
                ...b,
                name,
                welcomeMessage,
                avatarEmoji,
                systemPrompt,
                llmProvider,
                selectedModel,
                color,
                tone,
                apiKey
              }
            : b
        )
      );
      alert("Bot configuration saved & published successfully!");
      router.push(`/dashboard/${workspaceId}/bots/${currentChatbot.id}/deployment`);
    }
  };

  const handleSaveAppearance = async () => {
    try {
      const payload = {
        welcome_message: welcomeMessage,
        brand_color: color
      };
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save appearance settings");
      
      const updatedBot = await res.json();

      setChatbots((prev) =>
        prev.map((b) =>
          b.id === currentChatbot.id
            ? {
                ...b,
                welcomeMessage: updatedBot.welcome_message,
                color: updatedBot.brand_color,
                avatarEmoji
              }
            : b
        )
      );
      alert("Appearance saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Error saving appearance settings");
    }
  };

  // Helper to extract the last user query to dynamically compute source document matches
  const getLastUserMessageText = () => {
    const userMsgs = studioMessages.filter((m) => m.sender === "user");
    return userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].text.toLowerCase() : "";
  };

  const lastQuery = getLastUserMessageText();

  const getDynamicSource = () => {
    if (lastQuery.includes("refund")) {
      return { filename: "refund-policy.docx", match: "Page 2 · 98% match" };
    } else if (lastQuery.includes("pricing") || lastQuery.includes("plans")) {
      return { filename: "pricing-plans.pdf", match: "Page 1 · 95% match" };
    } else if (lastQuery.includes("onboard") || lastQuery.includes("how to")) {
      return { filename: "onboarding-guide.txt", match: "Page 1 · 91% match" };
    }
    return null;
  };

  const activeSource = getDynamicSource();

  // In the chatbot preview, override the first greeting message with our dynamic welcomeMessage
  const displayStudioMessages = [
    { sender: "bot" as const, text: welcomeMessage, time: "12:10 PM" },
    ...studioMessages.slice(1)
  ];

  const ToneIcon = TONE_ICONS[tone] || MessageCircle;
  const ModelIcon = MODEL_ICONS[selectedModel] || Zap;

  // AI Engine tab hides the preview widget and takes full width
  const isAiEngineTab = botStudioTab === "ai-engine";

  return (
    <div className="space-y-8 animate-fadeIn text-left max-w-5xl mx-auto">
      {/* Title & Publish Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-[#0a1a2f] dark:text-white tracking-tight flex items-center gap-2.5">Bot Studio</h2>
          <p className="text-xs text-[#7c828a] mt-1 font-medium">Customize your assistant — configure settings, design appearance, and test sandbox</p>
        </div>

        <div className="flex items-center space-x-3.5 shrink-0 self-end sm:self-center">
          <button
            onClick={handleSaveSettings}
            className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-5 py-2.5 rounded-full text-xs font-bold border-0 cursor-pointer transition-colors shadow-sm"
          >
            Save & Publish
          </button>
        </div>
      </div>

      {/* Bot Info summary card */}
      <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm">
        <div className="space-y-2 text-left">
          <div className="flex items-center space-x-2">
            <span className="text-xl">{avatarEmoji}</span>
            <h3 className="text-base font-extrabold text-[#0a1a2f] dark:text-white">{name}</h3>
          </div>

          {/* Badge row */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="inline-flex items-center gap-1.5 bg-pink-50 text-pink-700 dark:bg-pink-500/10 dark:text-pink-400 border border-pink-100 dark:border-pink-500/20 px-3.5 py-1 rounded-full text-[10px] font-bold">
              <Bot className="w-3.5 h-3.5 text-pink-500 shrink-0" />
              SaaS Assistant
            </span>
            <span className="inline-flex items-center gap-1.5 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border border-amber-100 dark:border-amber-500/20 px-3.5 py-1 rounded-full text-[10px] font-bold">
              <ModelIcon className="w-3.5 h-3.5 text-amber-500 shrink-0" />
              {llmProvider} ({selectedModel})
            </span>
            <span className="inline-flex items-center gap-1.5 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20 px-3.5 py-1 rounded-full text-[10px] font-bold">
              <ToneIcon className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
              {tone}
            </span>
            <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-450 border border-emerald-100 dark:border-emerald-500/20 px-3.5 py-1 rounded-full text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              Live
            </span>
          </div>
        </div>

        {/* Metrics Row */}
        <div className="flex gap-4 shrink-0 self-end md:self-center">
          <div className="px-5 py-2.5 rounded-2xl bg-[#f7f7f7] dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-center min-w-[100px] shadow-sm">
            <p className="text-xl font-black text-emerald-500 dark:text-emerald-450">94%</p>
            <p className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-0.5">Answer quality</p>
          </div>
          <div className="px-5 py-2.5 rounded-2xl bg-[#f7f7f7] dark:bg-slate-900 border border-slate-200 dark:border-white/10 text-center min-w-[100px] shadow-sm">
            <p className="text-xl font-black text-[#0052ff] dark:text-blue-400">24</p>
            <p className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-0.5">Total chats</p>
          </div>
        </div>
      </div>

      {/* Main Settings/Editor Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
        {/* Editor (Left column) */}
        <div className={`${isAiEngineTab ? "lg:col-span-5" : "lg:col-span-3"} space-y-6`}>
          {/* Editor Header Tab Bar */}
          <div className="flex overflow-x-auto scrollbar-none border-b border-slate-200 dark:border-white/5 whitespace-nowrap gap-2 pb-px">
            {[
              { id: "ai-engine", label: "AI Engine", icon: Cpu },
              { id: "appearance", label: "Appearance", icon: Palette },
              { id: "language", label: "Language", icon: Globe },
              { id: "preview", label: "Preview Sandbox", icon: MessageSquare }
            ].map((tab) => {
              const isActive = botStudioTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setBotStudioTab(tab.id as any)}
                  className={`flex items-center gap-1.5 h-9 px-3.5 text-xs font-semibold transition-colors focus:outline-none relative cursor-pointer ${
                    isActive ? "text-[#0052ff]" : "text-[#5b616e] hover:text-[#0a0b0d] dark:text-slate-400 dark:hover:text-white"
                  } bg-transparent border-0`}
                >
                  <tab.icon size={13} className={isActive ? "text-[#0052ff]" : "text-[#a8acb3]"} />
                  {tab.label}
                  {isActive && <span className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-[#0052ff] rounded-t-full" />}
                </button>
              );
            })}
          </div>

          {/* TAB CONTENT: AI Engine */}
          {botStudioTab === "ai-engine" && (
            <div className="space-y-5 animate-fadeIn">
              
              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 dark:border-white/5">
                  <h3 className="text-xs font-semibold text-[#0a0b0d] dark:text-white">AI Model</h3>
                </div>
                <div className="p-5 space-y-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">LLM Provider</label>
                      <select
                        value={llmProvider}
                        onChange={(e) => {
                          const prov = e.target.value;
                          setLlmProvider(prov);
                          setSelectedModel(PROVIDER_MODELS[prov]?.[0] || "");
                        }}
                        className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                      >
                        <option value="OpenAI">OpenAI</option>
                        <option value="Groq">Groq</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Select Model</label>
                      <select
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                      >
                        {(PROVIDER_MODELS[llmProvider] || []).map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Provider API Key</label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-proj-..."
                      className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 dark:border-white/5">
                  <h3 className="text-xs font-semibold text-[#0a0b0d] dark:text-white">Behaviour & Tone</h3>
                </div>
                <div className="p-5 space-y-5">
                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">System prompt rules</label>
                    <textarea
                      rows={6}
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                      placeholder="You are a helpful assistant..."
                      className="w-full px-3 py-2.5 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none resize-none font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Response Personality Tone</label>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    >
                      <option value="Friendly">Friendly &amp; Warm</option>
                      <option value="Professional">Professional &amp; Polite</option>
                      <option value="Playful">Playful &amp; Creative</option>
                      <option value="Technical">Technical &amp; Structured</option>
                    </select>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB CONTENT: Appearance */}
          {botStudioTab === "appearance" && (
            <div className="space-y-5 animate-fadeIn">
              
              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 dark:border-white/5">
                  <h3 className="text-xs font-semibold text-[#0a0b0d] dark:text-white">Customize</h3>
                </div>
                <div className="p-5 space-y-5">
                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Welcome Message</label>
                    <input
                      type="text"
                      value={welcomeMessage}
                      onChange={(e) => setWelcomeMessage(e.target.value)}
                      placeholder="How can I help you today?"
                      className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Bot avatar emoji</label>
                      <input
                        type="text"
                        value={avatarEmoji}
                        onChange={(e) => setAvatarEmoji(e.target.value)}
                        placeholder="🤖"
                        maxLength={2}
                        className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none text-center font-bold text-lg"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Choose Brand color Accent</label>
                      <div className="flex items-center gap-2 pt-1">
                        {["#0052ff", "#10B981", "#EC4899", "#8B5CF6", "#F59E0B"].map((c) => (
                          <button
                            key={c}
                            onClick={() => setColor(c)}
                            className={`w-8 h-8 rounded-full border-2 transition-transform ${
                              color === c ? "scale-110 border-[#0a0b0d] dark:border-white" : "border-transparent"
                            }`}
                            style={{ backgroundColor: c }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Hex Value</label>
                    <div className="flex items-center space-x-2.5 bg-[#f7f7f7] dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3.5 h-9 max-w-[200px]">
                      <input
                        type="color"
                        value={color}
                        onChange={(e) => setColor(e.target.value)}
                        className="w-5 h-5 rounded border-0 cursor-pointer bg-transparent"
                      />
                      <span className="font-mono text-xs font-bold uppercase text-slate-700 dark:text-slate-300">
                        {color}
                      </span>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-200 dark:border-white/5 flex justify-end">
                    <button
                      onClick={handleSaveAppearance}
                      className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer border-0 shadow-sm transition-colors"
                    >
                      Save Appearance
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB CONTENT: Language */}
          {botStudioTab === "language" && (
            <div className="space-y-4 animate-fadeIn">
              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 dark:border-white/5">
                  <h3 className="text-xs font-semibold text-[#0a0b0d] dark:text-white">Language settings</h3>
                </div>
                <div className="p-5 space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-[#5b616e] uppercase tracking-wide mb-1.5">Default greeting language</label>
                    <select className="w-full h-9 px-3 border border-slate-200 dark:border-white/10 rounded-xl text-xs bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none">
                      <option>English (US)</option>
                      <option>Spanish (ES)</option>
                      <option>French (FR)</option>
                      <option>German (DE)</option>
                    </select>
                  </div>
                  <p className="text-[10px] text-[#7c828a] leading-normal font-medium">
                    DocuBot detects your user's browser language automatically to translate greeting steps contextually.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB CONTENT: Preview Sandbox */}
          {botStudioTab === "preview" && (
            <div className="space-y-6 animate-fadeIn">
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-[#0a1a2f] dark:text-white uppercase tracking-wider">Preview Sandbox Tab</h4>
                <p className="text-xs text-[#7c828a] leading-relaxed font-medium">
                  Test configuration updates here instantly. Test query inputs containing words like "pricing", "plans", "onboard", or "refunds" to try response flows.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
                {/* Chat sandbox area */}
                <div className="md:col-span-2 border border-slate-200 dark:border-white/5 rounded-2xl bg-white dark:bg-[#0d111b] p-4 shadow-sm flex flex-col h-[400px]">
                  <div className="flex-1 overflow-y-auto space-y-4 pr-1 flex flex-col">
                    {displayStudioMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-2xl max-w-[85%] text-xs leading-relaxed flex flex-col ${
                          msg.sender === "user"
                            ? "bg-[#0052ff] text-white self-end rounded-br-none shadow-sm"
                            : "bg-[#f7f7f7] dark:bg-slate-900 text-[#0a0b0d] dark:text-slate-250 self-start rounded-bl-none border border-slate-200/50 dark:border-white/5"
                        }`}
                      >
                        <span className="whitespace-pre-line">{msg.text}</span>
                        <span className={`text-[8px] self-end mt-1.5 ${msg.sender === "user" ? "text-white/60" : "text-slate-400 dark:text-slate-550"}`}>
                          {msg.time}
                        </span>
                      </div>
                    ))}

                    {studioIsTyping && (
                      <div className="bg-[#f7f7f7] dark:bg-slate-900 border border-slate-200 dark:border-white/5 p-3 rounded-2xl self-start rounded-bl-none flex items-center space-x-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-2 py-3 border-t border-slate-100 dark:border-white/5 mt-3">
                    <button
                      type="button"
                      onClick={() => handleSendStudioMessage(undefined, "Pricing plans?")}
                      className="px-3.5 py-1.5 rounded-full bg-[#f7f7f7] hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-800 text-[10px] font-bold text-slate-800 dark:text-slate-200 border border-slate-200/50 dark:border-white/5 cursor-pointer"
                    >
                      Pricing plans?
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSendStudioMessage(undefined, "Refund policy?")}
                      className="px-3.5 py-1.5 rounded-full bg-[#f7f7f7] hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-800 text-[10px] font-bold text-slate-800 dark:text-slate-200 border border-slate-200/50 dark:border-white/5 cursor-pointer"
                    >
                      Refund policy?
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSendStudioMessage(undefined, "How to onboard?")}
                      className="px-3.5 py-1.5 rounded-full bg-[#f7f7f7] hover:bg-slate-100 dark:bg-slate-900 dark:hover:bg-slate-800 text-[10px] font-bold text-slate-800 dark:text-slate-200 border border-slate-200/50 dark:border-white/5 cursor-pointer"
                    >
                      How to onboard?
                    </button>
                  </div>

                  <form onSubmit={handleSendStudioMessage} className="pt-3 border-t border-slate-100 dark:border-white/5 flex gap-3">
                    <input
                      type="text"
                      placeholder="Ask a question..."
                      value={studioInput}
                      onChange={(e) => setStudioInput(e.target.value)}
                      className="flex-1 h-9 px-3 bg-[#f7f7f7] dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl text-xs text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    />
                    <button
                      type="submit"
                      className="bg-[#0052ff] hover:bg-[#003ecc] text-white h-9 px-5 rounded-xl text-xs font-bold transition-all shadow-md cursor-pointer border-0 shrink-0"
                    >
                      Send
                    </button>
                  </form>
                </div>

                {/* Sources list area */}
                <div className="border border-slate-200 dark:border-white/5 rounded-2xl bg-white dark:bg-[#0d111b] p-4 shadow-sm h-[400px]">
                  <h5 className="text-[10px] text-slate-400 dark:text-slate-555 font-extrabold uppercase tracking-widest border-b border-slate-100 dark:border-white/5 pb-2">
                    SOURCES
                  </h5>
                  {activeSource ? (
                    <div className="p-3.5 rounded-xl border border-slate-100 dark:border-white/5 bg-[#f7f7f7] dark:bg-slate-900/80 space-y-1 mt-3">
                      <h4 className="text-xs font-bold text-slate-950 dark:text-white truncate">
                        {activeSource.filename}
                      </h4>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                        {activeSource.match}
                      </p>
                    </div>
                  ) : (
                    <p className="text-[11px] text-[#7c828a] leading-relaxed mt-4 text-center font-medium">
                      Ask a query in sandbox to display the retrieved RAG source document.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Preview Device Widget (Right column - hidden on AI Engine Tab) */}
        {!isAiEngineTab && (
          <div className="lg:col-span-2 p-6 rounded-3xl bg-white dark:bg-[#0d111b] border border-slate-200 dark:border-white/5 flex flex-col items-center justify-center space-y-6 shadow-sm">
            <div className="text-center">
              <h4 className="text-xs font-bold text-[#0a1a2f] dark:text-white uppercase tracking-wider flex items-center gap-1.5 justify-center">
                <Brain className="w-4 h-4 text-[#0052ff]" /> Live Preview widget
              </h4>
              <p className="text-[10px] text-[#7c828a] mt-0.5 font-medium">Shows active changes in real-time</p>
            </div>

            <div className="w-full max-w-[320px] bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/5 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[380px]">
              {/* Widget header */}
              <div className="p-4 flex items-center space-x-3 text-white transition-colors duration-300" style={{ backgroundColor: color }}>
                <div className="w-8 h-8 rounded-full bg-white/15 flex items-center justify-center text-sm">{avatarEmoji}</div>
                <div className="flex-1 min-w-0 font-bold text-xs truncate">
                  {name || "Product Docs Bot"}
                </div>
              </div>

              {/* Widget Chat Window */}
              <div className="flex-1 p-3 overflow-y-auto space-y-3.5 flex flex-col justify-end bg-slate-50 dark:bg-slate-950">
                {/* Connection Status / Error Banner */}
                {connectionStatus === "connecting" && (
                  <div className="text-center text-[10px] text-[#7c828a] py-1">Connecting to Playground...</div>
                )}
                {error && (
                  <div className="text-center text-[10px] text-rose-500 py-1 bg-rose-50 dark:bg-rose-900/20 rounded-md border border-rose-200 dark:border-rose-800">
                    {error}
                  </div>
                )}
                
                {displayStudioMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    style={msg.sender === 'user' ? { backgroundColor: color } : undefined}
                    className={`p-3 rounded-xl max-w-[85%] text-xs leading-normal flex flex-col ${
                      msg.sender === "user"
                        ? "text-white self-end rounded-br-none shadow-sm"
                        : "bg-white dark:bg-[#0d111b] text-slate-800 dark:text-slate-250 self-start rounded-bl-none border border-slate-200 dark:border-white/5 shadow-sm"
                    }`}
                  >
                    <span>{msg.text}</span>
                  </div>
                ))}

                {studioIsTyping && (
                  <div className="bg-white dark:bg-[#0d111b] border border-slate-200 dark:border-white/5 p-2.5 rounded-xl self-start rounded-bl-none flex items-center space-x-1 shadow-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-450 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                )}
              </div>

              {/* Widget Input Form */}
              <form onSubmit={handleSendStudioMessage} className="p-2.5 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-white/5 flex gap-2">
                <input
                  type="text"
                  placeholder="Ask preview..."
                  value={studioInput}
                  onChange={(e) => setStudioInput(e.target.value)}
                  className="flex-1 bg-[#f7f7f7] dark:bg-[#0d111b] border border-slate-200 dark:border-white/5 rounded-xl px-3 py-2 text-xs text-[#0a0b0d] dark:text-white focus:outline-none"
                />
                <button
                  type="submit"
                  className="p-2 text-white rounded-xl border-0 cursor-pointer shadow-sm hover:opacity-90 transition-opacity"
                  style={{ backgroundColor: color }}
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
