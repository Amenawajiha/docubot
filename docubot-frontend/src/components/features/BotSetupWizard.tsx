"use client";

import React, { useState, useRef, useEffect } from "react";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import {
  Check,
  ArrowLeft,
  ArrowRight,
  Settings,
  Zap,
  X,
  Upload,
  FileText,
  Globe,
  Lock,
  Sparkles,
  Loader2,
  Rocket,
  ChevronRight,
  Sparkle,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { usePlayground } from "@/hooks/usePlayground";
import congratulationsAnimation from "../../../public/images/Congratulations.json";
import {
  StatusBadge,
  ProgressBar,
  ToneSelector,
  MODELS,
  TONE_DESCRIPTIONS,
} from "@/components/ui/shared-dashboard";
import dynamic from "next/dynamic";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

type CreateMode = "choose" | "quick" | "advanced";
type QuickPhase =
  | "upload"
  | "processing"
  | "playground"
  | "deploying"
  | "success";
type Step = 1 | 2 | 3 | 4 | 5 | 6 | 7;

const QC_BUILD_STEPS = [
  "Reading uploaded documents",
  "Building knowledge base",
  "Generating chatbot instructions",
  "Creating welcome message",
  "Optimizing AI responses",
];

const QC_DEPLOY_STAGES = [
  { label: "Preparing deployment", duration: 700 },
  { label: "Publishing knowledge base", duration: 800 },
  { label: "Going live", duration: 600 },
];

export default function BotSetupWizard() {
  const router = useRouter();
  const { workspaceId, changeCurrentChatbot, setChatbots, currentChatbot } =
    useWorkspace();
  const { sendMessage } = usePlayground(workspaceId, currentChatbot?.id);
  const [mode, setMode] = useState<CreateMode>("choose");
  const [step, setStep] = useState<Step>(1);

  // Form Data
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [welcome, setWelcome] = useState("👋 Hi! How can I help you today?");
  const [color, setColor] = useState("#0052ff");
  const [selectedModel, setSelectedModel] = useState("openai/gpt-oss-20b");
  const [tone, setTone] = useState("friendly");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const [lottieData, setLottieData] = useState<unknown>(null);
  const [plan, setPlan] = useState<"starter" | "pro">("starter");

  // Local states for Progressive API Integration
  const [isCreatingBot, setIsCreatingBot] = useState(false);
  const [localUploadedFiles, setLocalUploadedFiles] = useState<any[]>([]);
  const [localIsTraining, setLocalIsTraining] = useState(false);
  const [localTrainingProgress, setLocalTrainingProgress] = useState(0);
  const [uploadMethod, setUploadMethod] = useState<"file" | "url">("file");
  const [inputUrl, setInputUrl] = useState("");
  const [isPaying, setIsPaying] = useState(false);
  const [embedScript, setEmbedScript] = useState("");
  const [localEmbedCodeCopied, setLocalEmbedCodeCopied] = useState(false);

  // TODO: Add logic to fetch and resume Draft/Inactive bots from workspace if the user left off midway through

  const [copied, setCopied] = useState<"url" | "embed" | null>(null);

  const copyToClipboard = (text: string, key: "url" | "embed") => {
    const fallback = (t: string) => {
      const el = document.createElement("textarea");
      el.value = t;
      el.style.cssText = "position:fixed;top:-9999px;left:-9999px;opacity:0";
      document.body.appendChild(el);
      el.focus();
      el.select();
      try {
        document.execCommand("copy");
      } catch {}
      document.body.removeChild(el);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => fallback(text));
    } else {
      fallback(text);
    }
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const [buildDone, setBuildDone] = useState(0);
  const [buildComplete, setBuildComplete] = useState(false);
  const [deployStage, setDeployStage] = useState(0);
  const [deployProgress, setDeployProgress] = useState(0);
  const [deployReady, setDeployReady] = useState(false);
  const [quickPhase, setQuickPhase] = useState<QuickPhase>("upload");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if ((quickPhase === "success" || step === 7) && !lottieData) {
      fetch("/images/Congratulations.json")
        .then((res) => res.json())
        .then((data) => setLottieData(data))
        .catch((err) => console.error("Failed to load Lottie:", err));
    }
  }, [quickPhase, step, lottieData]);

  // Play sandbox message state
  const [playMessages, setSandboxMessages] = useState<
    { role: "user" | "bot"; text: string }[]
  >([{ role: "bot", text: welcome }]);
  const [userInput, setUserInput] = useState("");
  const [sandboxLoading, setSandboxLoading] = useState(false);

  const localCopyEmbedCode = () => {
    navigator.clipboard.writeText(embedScript);
    setLocalEmbedCodeCopied(true);
    setTimeout(() => setLocalEmbedCodeCopied(false), 2000);
  };

  const handleLocalFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArr = Array.from(e.target.files);
      const newFiles = filesArr.map((f) => ({
        id: `pending-${Math.random()}`,
        name: f.name,
        size: (f.size / 1024 / 1024).toFixed(2) + " MB",
        type: f.name.split(".").pop()?.toUpperCase() || "PDF",
        uploadedAt: new Date().toISOString().split("T")[0],
        status: "Uploading",
        fileObj: f,
      }));
      setLocalUploadedFiles((prev) => [...prev, ...newFiles]);

      for (const file of newFiles) {
        const formData = new FormData();
        formData.append("file", file.fileObj);
        try {
          const res = await fetchApi(
            `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/upload`,
            {
              method: "POST",
              body: formData,
            },
          );
          const data = await res.json();
          setLocalUploadedFiles((prev) =>
            prev.map((f: any) =>
              f.id === file.id
                ? {
                    ...f,
                    id: data.document_id,
                    jobId: data.job_id,
                    status: "Processing",
                  }
                : f,
            ),
          );
        } catch (err) {
          setLocalUploadedFiles((prev) =>
            prev.map((f: any) =>
              f.id === file.id ? { ...f, status: "Failed" } : f,
            ),
          );
        }
      }
    }
  };

  const startLocalTraining = async (onComplete: () => void) => {
    setLocalIsTraining(true);
    setLocalTrainingProgress(10);
    const jobs = localUploadedFiles
      .filter((f: any) => f.jobId)
      .map((f: any) => f.jobId);
    if (jobs.length === 0) {
      setLocalIsTraining(false);
      onComplete();
      return;
    }

    const interval = setInterval(async () => {
      try {
        let allCompleted = true;
        let totalProgress = 0;
        for (const jobId of jobs) {
          const res = await fetchApi(
            `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/ingestion-jobs/${jobId}`,
          );
          const data = await res.json();
          totalProgress += data.progress_percent || 0;
          if (data.job_status !== "completed" && data.job_status !== "failed") {
            allCompleted = false;
          }
        }
        setLocalTrainingProgress(Math.floor(totalProgress / jobs.length));
        if (allCompleted) {
          clearInterval(interval);
          setLocalTrainingProgress(100);
          setTimeout(() => {
            setLocalIsTraining(false);
            onComplete();
          }, 800);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 2000);
  };

  const localRemoveFile = (id: string) => {
    setLocalUploadedFiles((prev) => prev.filter((f: any) => f.id !== id));
  };

  const handleBrowse = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleLocalFileUpload(e);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // mock an event object for handleFileUpload
      const mockEvent = {
        target: { files: e.dataTransfer.files },
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      handleLocalFileUpload(mockEvent);
    }
  };

  const canContinueUpload =
    localUploadedFiles.length > 0 || websiteUrl.trim().length > 0;

  const startBuilding = () => {
    if (websiteUrl.trim().length > 0) {
      // Trigger url submit logic in Providers
      // For now we just create a temp event, but Providers handles inputUrl
    }
    if (!canContinueUpload) return;
    setQuickPhase("processing");
    setBuildDone(0);
    setBuildComplete(false);
  };

  useEffect(() => {
    if (mode !== "quick" || quickPhase !== "processing") return;

    if (!localIsTraining && localUploadedFiles.length > 0) {
      startLocalTraining(() => {
        setBuildComplete(true);
        setTimeout(() => setQuickPhase("playground"), 800);
      });
    }

    // Map localTrainingProgress (0-100) to QC_BUILD_STEPS
    const stepIndex = Math.min(
      Math.floor((localTrainingProgress / 100) * QC_BUILD_STEPS.length),
      QC_BUILD_STEPS.length - 1,
    );
    // setBuildDone(stepIndex + 1);

    if (localTrainingProgress >= 100 && !buildComplete) {
      // setBuildComplete(true);
      setTimeout(() => {
        setQuickPhase("playground");
      }, 800);
    }
  }, [quickPhase, mode]);

  const startDeploy = () => {
    setDeployStage(0);
    setDeployProgress(0);
    setDeployReady(false);
    setQuickPhase("deploying");
  };

  async function handleDeploySuccess() {
    try {
      const payload = {
        name: name || "Quick Bot",
        brand_color: color,
        tone_preset: tone,
        custom_system_prompt: systemPrompt,
        llm_provider: "groq",
        llm_model: "openai/gpt-oss-20b",
      };

      const patchRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
      );

      if (!patchRes.ok) throw new Error("Failed to update bot");

      const deployRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/deploy`,
        { method: "POST" },
      );
      if (!deployRes.ok) throw new Error("Deploy failed");

      const channelRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/channels`,
        {
          method: "POST",
          body: JSON.stringify({
            channel_type: "widget",
            channel_name: "Web Widget",
            config: {},
            allowed_domains: [],
          }),
        },
      );
      if (channelRes.ok) {
        const channelData = await channelRes.json();
        const embedRes = await fetchApi(
          `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/channels/${channelData.id}/embed`,
        );
        if (embedRes.ok) {
          const embedData = await embedRes.json();
          setEmbedScript(embedData.embed_script);
          // Ideally save embed_script to local state, but we can rely on providers if we update it.
        }
      }
      setQuickPhase("success");
    } catch (err) {
      console.error(err);
      setQuickPhase("success");
    }
  }

  useEffect(() => {
    if (mode !== "quick" || quickPhase !== "deploying") return;
    let stage = 0;
    const runStage = () => {
      if (stage >= QC_DEPLOY_STAGES.length) {
        setDeployReady(true);
        setTimeout(() => {
          handleDeploySuccess();
        }, 600);
        return;
      }
      setDeployStage(stage);
      setDeployProgress(0);
      const duration = QC_DEPLOY_STAGES[stage].duration;
      const start = Date.now();
      const interval = setInterval(() => {
        const p = Math.min(100, ((Date.now() - start) / duration) * 100);
        setDeployProgress(p);
        if (p >= 100) {
          clearInterval(interval);
          stage += 1;
          runStage();
        }
      }, 30);
    };
    runStage();
  }, [quickPhase, mode]);

  const sendSandboxChat = () => {
    if (!userInput.trim()) return;
    sendMessage(userInput);
    setUserInput("");
  };

  const handleAdvancedStep1Submit = async () => {
    if (!name.trim()) {
      alert("Please provide a name for your bot");
      return;
    }
    setIsCreatingBot(true);
    try {
      const payload = {
        name: name,
        brand_color: color,
        tone_preset: tone.toLowerCase(),
        custom_system_prompt: desc,
        llm_provider: "groq",
        llm_model: "llama-3.3-70b-versatile",
      };

      const response = await fetchApi(`/workspaces/${workspaceId}/chatbots`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("Failed to create chatbot");
      }

      const data = await response.json();

      setChatbots((prev: any) => [
        {
          id: data.id,
          name: data.name,
          goal: "Support",
          status: "Inactive",
          chats: 0,
          docs: 0,
          plan: "Free",
          created: data.created_at || new Date().toISOString(),
          updated_at: data.updated_at || new Date().toISOString(),
          deployment_status: data.deployment_status || "draft",
          color: data.brand_color || color,
          tone: data.tone_preset || tone,
          systemPrompt: data.custom_system_prompt || desc,
          selectedModel: data.llm_model || "llama-3.3-70b-versatile",
          llmProvider: data.llm_provider || "groq",
        },
        ...prev,
      ]);

      if (changeCurrentChatbot) {
        changeCurrentChatbot(data.id);
      }
      setStep(2);
    } catch (error) {
      console.error(error);
      alert("Error creating chatbot. Please try again.");
    } finally {
      setIsCreatingBot(false);
    }
  };

  // ADVANCED wizard steps
  const nextStep = () => {
    if (step === 1 && !name.trim()) {
      alert("Please provide a name for your bot");
      return;
    }
    if (step < 7) setStep((s) => (s + 1) as Step);
  };
  const backStep = () => {
    if (step > 1) setStep((s) => (s - 1) as Step);
  };

  const handleAdvancedPublish = async () => {
    setIsPaying(true);
    try { 
      // Prevent publishing if the knowledge base is completely empty
      if (workspaceId && currentChatbot?.id) {
        const docsRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}/documents`);
        if (docsRes.ok) {
          const docs = await docsRes.json();
          if (!docs || docs.length === 0) {
            alert("Cannot publish: Knowledge base is empty. Please add documents first.");
            setIsPaying(false);
            return;
          }
        }
      }

      const provider = selectedModel.toLowerCase().includes("claude")
        ? "anthropic"
        : selectedModel.toLowerCase().includes("gemini")
          ? "google"
          : "groq";

      const patchRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            brand_color: color,
            tone_preset: tone.toLowerCase(),
            custom_system_prompt: systemPrompt || desc,
            llm_model: selectedModel,
            llm_provider: provider,
          }),
        },
      );

      if (!patchRes.ok) throw new Error("Failed to update bot configurations");

      const deployRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/deploy`,
        {
          method: "POST",
        },
      );

      if (!deployRes.ok) throw new Error("Failed to deploy chatbot");

      const channelRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/channels`,
        {
          method: "POST",
          body: JSON.stringify({
            channel_type: "widget",
            channel_name: "Web Widget",
            config: {},
            allowed_domains: [],
          }),
        },
      );

      if (!channelRes.ok) throw new Error("Failed to create channel");
      const channelData = await channelRes.json();

      const embedRes = await fetchApi(
        `/workspaces/${workspaceId}/chatbots/${currentChatbot?.id}/channels/${channelData.id}/embed`,
      );
      if (embedRes.ok) {
        const embedData = await embedRes.json();
        setEmbedScript(embedData.embed_script);
      }

      setStep(7);
    } catch (err) {
      console.error(err);
      alert("Error finalizing deployment. Please try again.");
    } finally {
      setIsPaying(false);
    }
  };

  if (mode === "choose") {
    return (
      <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-[#030712] -m-4 sm:-m-6 lg:-m-6 xl:-m-8 h-[calc(100vh-80px)]">
        {/* Header stick */}
        <div className="border-b border-[#dee1e6] dark:border-white/5 px-6 py-4 bg-white dark:bg-[#0d111b] shrink-0 sticky top-0 z-10">
          <div className="flex justify-between items-center mb-3">
            <button
              onClick={() => router.push(`/dashboard/${workspaceId}/bots`)}
              className="flex items-center gap-1 text-xs text-[#5b616e] dark:text-slate-400"
            >
              <ArrowLeft size={13} /> Cancel
            </button>
            <span className="text-[10px] font-bold text-[#7c828a]">
              Bot Setup • Step 1 of 4
            </span>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((s) => {
              const active = 1 === s;
              const completed = 1 > s;
              return (
                <div key={s} className="flex-1 flex items-center gap-2">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all duration-300 ${active ? "bg-[#0052ff] text-white ring-4 ring-[#0052ff]/20 scale-110" : completed ? "bg-[#05b169] text-white scale-100" : "bg-[#eef0f3] dark:bg-white/10 text-[#7c828a] scale-100"}`}
                  >
                    {completed ? <Check size={10} /> : s}
                  </div>
                  {s < 4 && (
                    <div className="flex-1 h-[2px] bg-[#eef0f3] dark:bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#05b169] transition-all duration-500 ease-out"
                        style={{ width: completed ? "100%" : "0%" }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-[#f7f7f7] dark:bg-[#030712] p-8 flex flex-col justify-center">
          <div className="max-w-2xl mx-auto w-full space-y-6 animate-fadeIn">
            <div className="text-center">
              <h1 className="text-xl font-semibold text-[#0a0b0d] dark:text-white tracking-tight mb-1">
                Create a Chatbot
              </h1>
              <p className="text-xs text-[#5b616e] dark:text-slate-400">
                Choose how you&apos;d like to get started building your virtual
                assistant.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border-2 border-[#0052ff] p-5 flex flex-col justify-between">
                <div>
                  <span className="text-[10px] font-bold text-[#0052ff] bg-[#f0f5ff] dark:bg-blue-900/10 px-2 py-0.5 rounded-full inline-block mb-3">
                    Recommended
                  </span>
                  <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white mb-1">
                    Quick Create
                  </p>
                  <p className="text-xs text-[#5b616e] dark:text-slate-400 mb-4">
                    Build a chatbot in under 2 minutes using your documents.
                  </p>
                  <ul className="text-xs text-[#5b616e] dark:text-slate-400 space-y-1.5 mb-5">
                    <li className="flex items-center gap-1.5">
                      <Check size={12} className="text-[#0052ff]" /> AI
                      configures everything automatically
                    </li>
                    <li className="flex items-center gap-1.5">
                      <Check size={12} className="text-[#0052ff]" /> No
                      technical setup required
                    </li>
                    <li className="flex items-center gap-1.5">
                      <Check size={12} className="text-[#0052ff]" /> Customize
                      later anytime
                    </li>
                  </ul>
                </div>
                <button
                  onClick={handleStartQuickCreate}
                  disabled={isCreatingBot}
                  className="w-full h-9 rounded-full bg-[#0052ff] hover:bg-[#003ecc] disabled:opacity-50 text-white text-xs font-semibold transition-colors"
                >
                  {isCreatingBot ? "Starting..." : "Start Quick Create"}
                </button>
              </div>
              <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5 flex flex-col justify-between">
                <div>
                  <span className="text-[10px] font-bold text-[#5b616e] bg-[#f7f7f7] dark:bg-white/5 px-2 py-0.5 rounded-full inline-block mb-3">
                    Advanced Options
                  </span>
                  <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white mb-1">
                    Advanced Builder
                  </p>
                  <p className="text-xs text-[#5b616e] dark:text-slate-400 mb-4 font-normal">
                    Configure every aspect of your chatbot before creating it.
                  </p>
                  <p className="text-[11px] text-[#7c828a] mb-5">
                    Best for experienced users who want custom prompts,
                    templates, and API wiring upfront.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setMode("advanced");
                    setStep(1);
                  }}
                  className="w-full h-9 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-semibold text-[#5b616e] dark:text-slate-400 hover:bg-[#f7f7f7] dark:hover:bg-white/5 bg-white dark:bg-[#0d111b] transition-colors"
                >
                  Open Advanced Builder
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  async function handleStartQuickCreate() {
    setIsCreatingBot(true);
    try {
      const payload = {
        name: "DocuBot Assistant",
        brand_color: "#0052ff",
        tone_preset: "professional",
        custom_system_prompt: "You are a helpful assistant.",
        llm_provider: "groq",
        llm_model: "openai/gpt-oss-20b",
      };
      const response = await fetchApi(`/workspaces/${workspaceId}/chatbots`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to create chatbot");
      const data = await response.json();

      setChatbots((prev: any) => [
        {
          ...payload,
          id: data.id,
          status: "Inactive",
          chats: 0,
          docs: 0,
          plan: "Free",
          created: new Date().toISOString(),
        },
        ...prev,
      ]);
      if (changeCurrentChatbot) changeCurrentChatbot(data.id);

      setMode("quick");
    } catch (err) {
      console.error(err);
      alert("Error starting Quick Create");
    } finally {
      setIsCreatingBot(false);
    }
  }

  // QUICK CREATE FLOW
  if (mode === "quick") {
    return (
      <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-[#030712] -m-4 sm:-m-6 lg:-m-6 xl:-m-8 h-[calc(100vh-80px)]">
        {/* Header stick */}
        <div className="border-b border-[#dee1e6] dark:border-white/5 px-6 py-4 bg-white dark:bg-[#0d111b] shrink-0 sticky top-0 z-10">
          <div className="flex justify-between items-center mb-3">
            <button
              onClick={() => setMode("choose")}
              className="flex items-center gap-1 text-xs text-[#5b616e] dark:text-slate-400"
            >
              <ArrowLeft size={13} /> Back
            </button>
            <span className="text-[10px] font-bold text-[#7c828a]">
              Quick Setup • Step{" "}
              {quickPhase === "upload" || quickPhase === "processing"
                ? 2
                : quickPhase === "playground"
                  ? 3
                  : 4}{" "}
              of 4
            </span>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((s) => {
              const currentStep =
                quickPhase === "upload" || quickPhase === "processing"
                  ? 2
                  : quickPhase === "playground"
                    ? 3
                    : 4;
              const active = currentStep === s;
              const completed = currentStep > s;
              return (
                <div key={s} className="flex-1 flex items-center gap-2">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all duration-300 ${active ? "bg-[#0052ff] text-white ring-4 ring-[#0052ff]/20 scale-110" : completed ? "bg-[#05b169] text-white scale-100" : "bg-[#eef0f3] dark:bg-white/10 text-[#7c828a] scale-100"}`}
                  >
                    {completed ? <Check size={10} /> : s}
                  </div>
                  {s < 4 && (
                    <div className="flex-1 h-[2px] bg-[#eef0f3] dark:bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#05b169] transition-all duration-500 ease-out"
                        style={{ width: completed ? "100%" : "0%" }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Phase selector */}
        <div className="flex-1 overflow-y-auto py-4 px-6 flex flex-col justify-start">
          {quickPhase === "upload" && (
            <div className="max-w-md mx-auto w-full space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white">
                  Upload your documents
                </h2>
                <p className="text-xs text-[#5b616e] dark:text-slate-400 mt-0.5">
                  AI automatically configures and indexes your knowledge base.
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.docx,.csv,.xlsx,.pptx,.md,.epub,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
                className="hidden"
                onChange={handleBrowse}
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${dragging ? "border-[#0052ff] bg-[#f0f5ff] dark:bg-blue-900/10" : "border-[#dee1e6] dark:border-white/10 bg-[#f7f7f7]/30 hover:border-[#0052ff]/50"}`}
              >
                <Upload size={24} className="mx-auto mb-2 text-[#a8acb3]" />
                <p className="font-semibold text-xs text-[#0a0b0d] dark:text-white">
                  Drop files here or{" "}
                  <span className="text-[#0052ff]">browse</span>
                </p>
                <p className="text-[10px] text-[#7c828a] mt-0.5">
                  PDF, DOCX, PPTX, XLSX, CSV, MD, TXT, EPUB, Images
                </p>
              </div>

              {localUploadedFiles.length > 0 && (
                <div className="bg-white dark:bg-[#0d111b] rounded-xl border border-[#dee1e6] dark:border-white/5 divide-y divide-[#dee1e6] dark:divide-white/5">
                  {localUploadedFiles.map((file: any) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between px-3.5 py-2.5"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText size={13} className="text-[#0052ff]" />
                        <span className="text-xs text-[#0a0b0d] dark:text-white truncate max-w-[250px]">
                          {file.name}
                        </span>
                      </div>
                      <button
                        onClick={() => localRemoveFile(file.id)}
                        className="text-[#7c828a] hover:text-[#cf202f] cursor-pointer"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                  Website URL{" "}
                  <span className="font-normal text-[#7c828a]">(optional)</span>
                </label>
                <div className="flex items-center gap-2 h-9 px-3 border border-[#dee1e6] dark:border-white/10 rounded-xl bg-white dark:bg-[#0d111b]">
                  <Globe size={13} className="text-[#a8acb3]" />
                  <input
                    className="flex-1 text-xs outline-none bg-transparent placeholder:text-[#a8acb3] text-[#0a0b0d] dark:text-white"
                    placeholder="https://yoursite.com"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setMode("choose")}
                  className="h-9 px-4 rounded-full border border-[#dee1e6] text-xs font-semibold text-[#5b616e] dark:text-slate-400"
                >
                  Back
                </button>
                <button
                  disabled={!canContinueUpload}
                  onClick={startBuilding}
                  className="h-9 px-4 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-50"
                >
                  Build Chatbot <ArrowRight size={12} />
                </button>
              </div>
            </div>
          )}

          {quickPhase === "processing" && (
            <div className="max-w-xs mx-auto w-full space-y-4 text-center animate-fadeIn">
              <div className="w-12 h-12 rounded-2xl bg-[#f0f5ff]/60 mx-auto flex items-center justify-center">
                <Loader2 size={20} className="text-[#0052ff] animate-spin" />
              </div>
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                AI is building your chatbot
              </h2>
              <p className="text-xs text-[#7c828a]">
                Typical training setup is under 1 minute.
              </p>
              <ul className="text-left bg-white dark:bg-[#0d111b] rounded-xl border border-[#dee1e6] dark:border-white/5 divide-y divide-[#dee1e6] dark:divide-white/5 overflow-hidden">
                {QC_BUILD_STEPS.map((stepLabel, idx) => {
                  const done = idx < buildDone;
                  const active = idx === buildDone;
                  return (
                    <li
                      key={stepLabel}
                      className={`px-3 py-2 text-xs flex items-center gap-2 transition-opacity ${done || active ? "opacity-100" : "opacity-40"}`}
                    >
                      {done ? (
                        <Check size={11} className="text-[#05b169]" />
                      ) : active ? (
                        <Loader2
                          size={11}
                          className="animate-spin text-[#0052ff]"
                        />
                      ) : (
                        <div className="w-2.5 h-2.5 rounded-full bg-[#dee1e6] dark:bg-white/10" />
                      )}
                      <span
                        className={
                          done
                            ? "text-[#05b169]"
                            : "text-[#5b616e] dark:text-slate-400"
                        }
                      >
                        {stepLabel}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {quickPhase === "playground" && (
            <div className="max-w-xl mx-auto w-full animate-fadeIn flex flex-col min-h-0 gap-3">
              {/* Header text */}
              <div className="text-center">
                <h2 className="text-sm font-bold text-[#0a0b0d]">
                  Your chatbot is ready! 🎉
                </h2>
                <p className="text-[11px] text-[#7c828a] mt-0.5">
                  Try a quick sandbox test before deploying.
                </p>
              </div>

              {/* Chat Widget */}
              <div
                className="flex flex-col rounded-[20px] overflow-hidden shadow-[0_8px_40px_-12px_rgba(0,82,255,0.15)] border border-[#dee1e6]"
                style={{ height: 380 }}
              >
                {/* Widget Header */}
                <div className="flex items-center gap-3 px-4 py-3 bg-[#0052ff]">
                  <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center shrink-0">
                    <span className="text-white text-sm font-bold">
                      {(name || "B").charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-xs font-bold truncate">
                      {name || "Your Chatbot"}
                    </p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#6ee7b7] animate-pulse" />
                      <span className="text-white/70 text-[10px]">Online</span>
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
                    <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
                    <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
                  </div>
                </div>

                {/* Messages area */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-[#f7f8fc] flex flex-col">
                  {playMessages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.role === "bot" && (
                        <div className="w-6 h-6 rounded-full bg-[#0052ff] flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                          <span className="text-white text-[9px] font-bold">
                            {(name || "B").charAt(0).toUpperCase()}
                          </span>
                        </div>
                      )}
                      <div
                        className={`max-w-[78%] px-3 py-2 rounded-2xl text-xs leading-relaxed shadow-sm ${
                          msg.role === "user"
                            ? "bg-[#0052ff] text-white rounded-tr-none"
                            : "bg-white text-[#0a0b0d] rounded-tl-none border border-[#eef0f3]"
                        }`}
                      >
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  {sandboxLoading && (
                    <div className="flex gap-2 justify-start">
                      <div className="w-6 h-6 rounded-full bg-[#0052ff] flex items-center justify-center shrink-0 shadow-sm">
                        <span className="text-white text-[9px] font-bold">
                          {(name || "B").charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="bg-white border border-[#eef0f3] px-3 py-2 rounded-2xl rounded-tl-none flex gap-1 items-center shadow-sm">
                        {[0, 1, 2].map((j) => (
                          <span
                            key={j}
                            className="w-1.5 h-1.5 rounded-full bg-[#a8acb3] animate-bounce"
                            style={{ animationDelay: `${j * 0.15}s` }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Input bar */}
                <div className="px-4 py-3 bg-white border-t border-[#eef0f3] flex items-center gap-2">
                  <input
                    className="flex-1 text-xs outline-none bg-transparent placeholder:text-[#a8acb3] text-[#0a0b0d]"
                    placeholder="Type a message…"
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendSandboxChat()}
                  />
                  <button
                    onClick={sendSandboxChat}
                    className="h-8 w-8 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white flex items-center justify-center transition-colors shadow-sm shrink-0"
                  >
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setQuickPhase("upload")}
                  className="h-9 px-4 rounded-full border border-[#dee1e6] text-xs font-semibold text-[#5b616e]"
                >
                  Back
                </button>
                <button
                  onClick={startDeploy}
                  className="h-9 px-5 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                >
                  <Rocket size={12} /> Deploy Chatbot
                </button>
              </div>
            </div>
          )}

          {quickPhase === "deploying" && (
            <div className="max-w-xs mx-auto w-full space-y-4 text-center animate-fadeIn">
              <div className="w-12 h-12 rounded-2xl bg-[#e8f8f0] mx-auto flex items-center justify-center">
                <Loader2 size={20} className="text-[#05b169] animate-spin" />
              </div>
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Deploying your chatbot
              </h2>
              <div className="space-y-3 pt-2 text-left">
                {QC_DEPLOY_STAGES.map((s, idx) => {
                  const done = idx < deployStage || deployReady;
                  const active = idx === deployStage && !deployReady;
                  const progress = active ? deployProgress : done ? 100 : 0;
                  return (
                    <div key={s.label}>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span
                          className={done ? "text-[#05b169]" : "text-[#7c828a]"}
                        >
                          {s.label}
                        </span>
                        {active ? (
                          <span className="font-mono text-[10px] text-[#0052ff]">
                            {Math.round(progress)}%
                          </span>
                        ) : null}
                      </div>
                      <div className="w-full h-1.5 bg-[#eef0f3] dark:bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-75"
                          style={{
                            width: `${progress}%`,
                            backgroundColor: done ? "#05b169" : "#0052ff",
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {quickPhase === "success" && (
            <div className="max-w-2xl mx-auto w-full animate-fadeIn flex flex-col items-center py-2">
              {/* Lottie — big, centred, not clipped */}
              <div className="w-36 h-36 shrink-0 flex items-center justify-center">
                {lottieData ? (
                  <Lottie
                    animationData={lottieData as any}
                    loop
                    autoplay
                    style={{ width: 144, height: 144 }}
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-[#05b169] flex items-center justify-center">
                    <Check size={36} className="text-white" />
                  </div>
                )}
              </div>

              <h2 className="text-[22px] font-bold text-[#0a0b0d] tracking-tight mb-1 mt-1">
                🎉 Your chatbot is live!
              </h2>
              <p className="text-[12px] text-[#5b616e] text-center max-w-md mb-4">
                Congratulations! {name || "Your bot"} has been successfully
                deployed and is ready to assist your users.
              </p>

              <div className="w-full max-w-[600px] space-y-3">
                {/* URL Card */}
                <div className="bg-white border border-[#eef0f3] rounded-2xl p-2 pl-4 flex items-center justify-between shadow-[0_2px_8px_-4px_rgba(0,0,0,0.06)]">
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <Globe size={15} className="text-[#a8acb3] shrink-0" />
                    <span className="text-xs font-semibold text-[#0a0b0d] truncate">
                      https://chat.docubot.ai/
                      {name.toLowerCase().replace(/\s+/g, "-")}
                    </span>
                  </div>
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `https://chat.docubot.ai/${name.toLowerCase().replace(/\s+/g, "-")}`,
                        "url",
                      )
                    }
                    className={`h-9 px-4 text-[11px] font-bold rounded-xl shrink-0 transition-all duration-200 flex items-center gap-1.5 shadow-sm ${copied === "url" ? "bg-[#05b169] text-white" : "bg-[#0052ff] hover:bg-[#003ecc] text-white"}`}
                  >
                    {copied === "url" ? (
                      <>
                        <Check size={12} /> Copied!
                      </>
                    ) : (
                      <>
                        <FileText size={12} /> Copy Chatbot URL
                      </>
                    )}
                  </button>
                </div>

                {/* Embed Code Card */}
                <div className="space-y-1.5 text-left w-full max-w-[600px] mt-2">
                  <div className="flex items-center justify-between text-xs text-[#5b616e] dark:text-slate-400">
                    <span className="text-[10px] font-bold text-[#7c828a] tracking-wider">HTML EMBED TAG</span>
                    <button
                      onClick={localCopyEmbedCode}
                      className="hover:text-slate-900 dark:hover:text-white border-0 bg-transparent text-xs font-semibold cursor-pointer"
                    >
                      {localEmbedCodeCopied ? "Copied!" : "Copy code"}
                    </button>
                  </div>
                  <pre className="bg-slate-50 dark:bg-slate-950 border border-[#dee1e6] dark:border-white/5 rounded-xl p-3 text-[10px] text-indigo-700 dark:text-indigo-300 font-mono overflow-x-auto leading-relaxed whitespace-pre-wrap">
                    <code>{embedScript || "Generating embed script..."}</code>
                  </pre>
                </div>

                {/* 3 Action Buttons — modern card style */}
                <div className="grid grid-cols-3 gap-3">
                  {/* Open Chatbot */}
                  <button
                    onClick={() =>
                      window.open(
                        `https://chat.docubot.ai/${name.toLowerCase().replace(/\s+/g, "-")}`,
                        "_blank",
                      )
                    }
                    className="group relative flex flex-col items-center justify-center gap-2.5 h-[100px] bg-white border border-[#eef0f3] hover:border-[#0052ff]/30 rounded-2xl shadow-sm hover:shadow-[0_4px_20px_-6px_rgba(0,82,255,0.18)] transition-all duration-200 hover:-translate-y-0.5 overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-[#0052ff]/[0.04] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-2xl" />
                    <div className="w-10 h-10 rounded-xl bg-[#f0f5ff] group-hover:bg-[#0052ff] flex items-center justify-center transition-colors duration-200 shadow-sm">
                      <Globe
                        size={18}
                        className="text-[#0052ff] group-hover:text-white transition-colors duration-200"
                      />
                    </div>
                    <span className="text-[11px] font-semibold text-[#3d4350] group-hover:text-[#0052ff] transition-colors duration-200 relative">
                      Open Chatbot
                    </span>
                  </button>

                  {/* Copy Chatbot URL */}
                  <button
                    onClick={() =>
                      copyToClipboard(
                        `https://chat.docubot.ai/${name.toLowerCase().replace(/\s+/g, "-")}`,
                        "url",
                      )
                    }
                    className={`group relative flex flex-col items-center justify-center gap-2.5 h-[100px] bg-white border rounded-2xl shadow-sm transition-all duration-200 hover:-translate-y-0.5 overflow-hidden ${
                      copied === "url"
                        ? "border-[#05b169]/40 hover:border-[#05b169]/60"
                        : "border-[#eef0f3] hover:border-[#7c3aed]/30 hover:shadow-[0_4px_20px_-6px_rgba(124,58,237,0.18)]"
                    }`}
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-[#7c3aed]/[0.04] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-2xl" />
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-200 shadow-sm ${
                        copied === "url"
                          ? "bg-[#05b169]"
                          : "bg-[#f5f0ff] group-hover:bg-[#7c3aed]"
                      }`}
                    >
                      {copied === "url" ? (
                        <Check size={18} className="text-white" />
                      ) : (
                        <FileText
                          size={18}
                          className="text-[#7c3aed] group-hover:text-white transition-colors duration-200"
                        />
                      )}
                    </div>
                    <span
                      className={`text-[11px] font-semibold transition-colors duration-200 relative ${
                        copied === "url"
                          ? "text-[#05b169]"
                          : "text-[#3d4350] group-hover:text-[#7c3aed]"
                      }`}
                    >
                      {copied === "url" ? "Copied!" : "Copy Chatbot URL"}
                    </span>
                  </button>

                  {/* Dashboard */}
                  <button
                    onClick={() =>
                      router.push(`/dashboard/${workspaceId}/bots`)
                    }
                    className="group relative flex flex-col items-center justify-center gap-2.5 h-[100px] bg-white border border-[#eef0f3] hover:border-[#05b169]/30 rounded-2xl shadow-sm hover:shadow-[0_4px_20px_-6px_rgba(5,177,105,0.18)] transition-all duration-200 hover:-translate-y-0.5 overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-[#05b169]/[0.04] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-2xl" />
                    <div className="w-10 h-10 rounded-xl bg-[#ecfdf3] group-hover:bg-[#05b169] flex items-center justify-center transition-colors duration-200 shadow-sm">
                      <Check
                        size={18}
                        className="text-[#05b169] group-hover:text-white transition-colors duration-200"
                      />
                    </div>
                    <span className="text-[11px] font-semibold text-[#3d4350] group-hover:text-[#05b169] transition-colors duration-200 relative">
                      Dashboard
                    </span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ADVANCED BUILDER (7 Steps)
  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white dark:bg-[#030712] -m-4 sm:-m-6 lg:-m-6 xl:-m-8 h-[calc(100vh-80px)]">
      {/* Header stick */}
      <div className="border-b border-[#dee1e6] dark:border-white/5 px-6 py-4 bg-white dark:bg-[#0d111b] shrink-0 sticky top-0 z-10">
        <div className="flex justify-between items-center mb-3">
          <button
            onClick={() => setMode("choose")}
            className="flex items-center gap-1 text-xs text-[#5b616e] dark:text-slate-400"
          >
            <X size={13} /> Cancel
          </button>
          <span className="text-[10px] font-bold text-[#7c828a]">
            Advanced Wizard Step {step} of 7
          </span>
        </div>

        {/* Stepper Dots */}
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4, 5, 6, 7].map((s) => {
            const active = step === s;
            const completed = step > s;
            return (
              <div key={s} className="flex-1 flex items-center gap-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all duration-300 ${active ? "bg-[#0052ff] text-white ring-4 ring-[#0052ff]/20 scale-110" : completed ? "bg-[#05b169] text-white scale-100" : "bg-[#eef0f3] dark:bg-white/10 text-[#7c828a] scale-100"}`}
                >
                  {completed ? <Check size={10} /> : s}
                </div>
                {s < 7 && (
                  <div className="flex-1 h-[2px] bg-[#eef0f3] dark:bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#05b169] transition-all duration-500 ease-out"
                      style={{ width: completed ? "100%" : "0%" }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Steps Viewport */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8 flex flex-col justify-center">
        <div className="max-w-xl mx-auto w-full">
          {/* STEP 1: Basic Identity */}
          {step === 1 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Goal & Identity
              </h2>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                    Bot Name <span className="text-[#cf202f]">*</span>
                  </label>
                  <input
                    className="w-full h-9 px-3 border border-[#dee1e6] dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    placeholder="DocuBot Support Agent"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                    Description
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-[#dee1e6] dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none resize-none"
                    placeholder="Short summary of bot functions…"
                    rows={3}
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Knowledge Ingestion */}
          {step === 2 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Knowledge Source Setup
              </h2>
              <p className="text-xs text-[#7c828a]">
                Add websites or documents to teach your AI.
              </p>

              <div
                className="border-2 border-dashed border-[#dee1e6] dark:border-white/10 rounded-2xl p-6 text-center bg-[#f7f7f7]/30 hover:border-[#0052ff]/40 transition-colors cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleLocalFileUpload}
                  multiple
                  className="hidden"
                  accept=".pdf,.txt,.docx"
                />
                <Upload size={24} className="mx-auto mb-2 text-[#a8acb3]" />
                <p className="font-semibold text-xs text-[#0a0b0d] dark:text-white">
                  Click to upload files
                </p>
                <p className="text-[10px] text-[#7c828a]">
                  PDF � DOCX � TXT � CSV
                </p>
              </div>

              {localUploadedFiles.length > 0 && (
                <div className="bg-white dark:bg-[#0d111b] rounded-xl border border-[#dee1e6] dark:border-white/5 divide-y divide-[#dee1e6] dark:divide-white/5">
                  {localUploadedFiles.map((file: any) => (
                    <div
                      key={file.id}
                      className="flex items-center justify-between px-3 py-2 text-xs"
                    >
                      <span className="text-[#0a0b0d] dark:text-white truncate">
                        {file.name} - {file.status}
                      </span>
                      <button
                        onClick={() => localRemoveFile(file.id)}
                        className="text-[#cf202f] cursor-pointer hover:underline"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {localUploadedFiles.length > 0 && (
                <div className="pt-2">
                  {localTrainingProgress === 100 ? (
                    <div className="p-3 bg-[#e8f8f0] border border-[#05b169]/30 rounded-xl text-center">
                      <p className="text-xs font-semibold text-[#05b169] flex items-center justify-center gap-1.5">
                        <Check size={14} /> Knowledge Ingestion Completed!
                      </p>
                      <p className="text-[10px] text-[#5b616e] mt-0.5">Click "Next Step" below to configure your bot appearance.</p>
                    </div>
                  ) : (
                    <button
                      onClick={() => startLocalTraining(() => {})}
                      disabled={localIsTraining}
                      className="w-full h-9 rounded-full bg-[#0052ff] text-white text-xs font-semibold disabled:opacity-50"
                    >
                      {localIsTraining
                        ? `Training... ${localTrainingProgress}%`
                        : "Start Processing"}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Customize Widget appearance */}
          {step === 3 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Branding & Customize
              </h2>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                    Brand Accent Color
                  </label>
                  <div className="flex gap-2">
                    {[
                      "#0052ff",
                      "#05b169",
                      "#f4b000",
                      "#cf202f",
                      "#7c3aed",
                      "#0a0b0d",
                    ].map((c) => (
                      <button
                        key={c}
                        onClick={() => setColor(c)}
                        className={`w-7 h-7 rounded-full border-2 transition-all ${color === c ? "border-[#0a0b0d] dark:border-white scale-110 shadow-sm" : "border-transparent hover:scale-105"}`}
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                    Welcome Message
                  </label>
                  <input
                    className="w-full h-9 px-3 border border-[#dee1e6] dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    value={welcome}
                    onChange={(e) => setWelcome(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: AI Brain & Prompt */}
          {step === 4 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                AI Engine
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-2">
                    Select LLM Model
                  </label>
                  <div className="grid grid-cols-1 gap-2.5">
                    {[
                      { id: "openai/gpt-oss-20b", name: "openai/gpt-oss-20b", provider: "Groq", badge: "Recommended", desc: "Best for general intelligence, logic, and speed." },
                      { id: "llama-3.1-8b-instant", name: "llama-3.1-8b-instant", provider: "Groq", badge: "Fastest", desc: "Ultra-low latency for instant chat responses." },
                      { id: "llama-3.3-70b-versatile", name: "llama-3.3-70b-versatile", provider: "Groq", badge: "Powerful", desc: "High reasoning capacity for complex support queries." },
                    ].map((m) => (
                      <div
                        key={m.id}
                        onClick={() => setSelectedModel(m.id)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                          selectedModel === m.id
                            ? "border-[#0052ff] bg-[#f0f5ff] dark:bg-blue-900/10 shadow-sm"
                            : "border-[#dee1e6] dark:border-white/10 hover:border-[#0052ff]/40"
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[#0a0b0d] dark:text-white">{m.name}</span>
                            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-[#eef0f3] dark:bg-white/10 text-[#5b616e] dark:text-slate-300">{m.badge}</span>
                          </div>
                          <p className="text-[11px] text-[#7c828a] mt-0.5">{m.desc}</p>
                        </div>
                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${selectedModel === m.id ? "border-[#0052ff] bg-[#0052ff]" : "border-[#dee1e6]"}`}>
                          {selectedModel === m.id && <Check size={10} className="text-white" />}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#5b616e] mb-1.5">
                    System Rule Prompt
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-[#dee1e6] dark:border-white/10 rounded-xl text-xs bg-white dark:bg-[#0d111b] text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none font-mono resize-none"
                    rows={4}
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    placeholder="Define boundaries and default response actions�"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: Final review */}
          {step === 5 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Review Settings
              </h2>
              <div className="bg-[#f7f7f7] dark:bg-white/5 rounded-2xl border border-[#dee1e6] dark:border-white/5 p-4 space-y-3.5 text-xs text-[#5b616e] dark:text-slate-350">
                <div className="flex justify-between border-b border-[#dee1e6] dark:border-white/5 pb-1.5">
                  <span className="font-semibold">Bot Name</span>
                  <span className="font-bold text-[#0a0b0d] dark:text-white">
                    {name || "—"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-[#dee1e6] dark:border-white/5 pb-1.5">
                  <span className="font-semibold">Selected Model</span>
                  <span className="font-bold text-[#0a0b0d] dark:text-white">
                    {selectedModel}
                  </span>
                </div>
                <div className="flex justify-between border-b border-[#dee1e6] dark:border-white/5 pb-1.5">
                  <span className="font-semibold">TonePreset</span>
                  <span className="font-bold text-[#0a0b0d] dark:text-white uppercase">
                    {tone}
                  </span>
                </div>
                <div className="flex justify-between pb-1.5">
                  <span className="font-semibold">Knowledge base sources</span>
                  <span className="font-bold text-[#0a0b0d] dark:text-white">
                    {localUploadedFiles.length} documents
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 6: Pricing Tier */}
          {step === 6 && (
            <div className="space-y-4 animate-fadeIn">
              <h2 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">
                Choose Subscription
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div
                  onClick={() => setPlan("starter")}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${plan === "starter" ? "border-[#0052ff] bg-[#f0f5ff] dark:bg-blue-900/10" : "border-[#dee1e6] dark:border-white/10"}`}
                >
                  <p className="font-semibold text-xs text-[#0a0b0d] dark:text-white">
                    Starter Tier
                  </p>
                  <p className="text-[10px] text-[#7c828a] mt-1">
                    1.5k chats · $19/mo
                  </p>
                </div>
                <div
                  onClick={() => setPlan("pro")}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${plan === "pro" ? "border-[#0052ff] bg-[#f0f5ff] dark:bg-blue-900/10" : "border-[#dee1e6] dark:border-white/10"}`}
                >
                  <p className="font-semibold text-xs text-[#0a0b0d] dark:text-white">
                    Professional Tier
                  </p>
                  <p className="text-[10px] text-[#7c828a] mt-1">
                    15k chats · $49/mo
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* STEP 7: Publishing success */}
          {step === 7 && (
            <div className="space-y-4 text-center animate-fadeIn">
              {lottieData ? (
                <div className="mx-auto w-32 h-32 flex items-center justify-center">
                  <Lottie animationData={lottieData as any} loop={false} />
                </div>
              ) : null}
              <h2 className="text-xl font-semibold text-[#0a0b0d] dark:text-white">
                Bot Published Successfully!
              </h2>
              <p className="text-xs text-[#5b616e] dark:text-slate-400">
                Your chatbot is now live and ready to be integrated.
              </p>

              <div className="space-y-1.5 text-left max-w-md mx-auto mt-6">
                <div className="flex items-center justify-between text-xs text-[#5b616e] dark:text-slate-400">
                  <span>HTML embed tag</span>
                  <button
                    onClick={localCopyEmbedCode}
                    className="hover:text-slate-900 dark:hover:text-white border-0 bg-transparent text-xs font-semibold cursor-pointer"
                  >
                    {localEmbedCodeCopied ? "Copied!" : "Copy code"}
                  </button>
                </div>
                <pre className="bg-slate-50 dark:bg-slate-950 border border-[#dee1e6] dark:border-white/5 rounded-xl p-3 text-[10px] text-indigo-700 dark:text-indigo-300 font-mono overflow-x-auto leading-relaxed">
                  <code>{embedScript || "Generating embed script..."}</code>
                </pre>
              </div>

              <button
                onClick={() => router.push(`/dashboard/${workspaceId}/bots`)}
                className="mt-6 w-full h-10 bg-[#0052ff] hover:bg-[#003ecc] text-white rounded-full text-xs font-semibold transition-colors"
              >
                Go to Dashboard
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Footer / Controls */}
      <div className="border-t border-[#dee1e6] dark:border-white/5 bg-white dark:bg-[#0d111b] p-4 flex justify-between items-center shrink-0">
        <button
          onClick={() => {
            if (step === 1) {
              setMode("choose");
            } else {
              backStep();
            }
          }}
          className="h-9 px-4 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-semibold text-[#5b616e] dark:text-slate-400 hover:bg-[#f7f7f7] dark:hover:bg-white/5 bg-white dark:bg-[#0d111b] transition-colors flex items-center gap-2"
        >
          <ArrowLeft size={13} /> {step === 1 ? "Cancel" : "Back"}
        </button>

        {step < 7 && (
          <button
            onClick={() => {
              if (step === 1) {
                handleAdvancedStep1Submit();
              } else if (step === 6) {
                handleAdvancedPublish();
              } else {
                nextStep();
              }
            }}
            disabled={isCreatingBot || isPaying}
            className="h-9 px-6 rounded-full bg-[#0052ff] hover:bg-[#003ecc] text-white text-xs font-semibold transition-colors flex items-center gap-2"
          >
            {step === 6
              ? isPaying
                ? "Deploying..."
                : "Publish Bot"
              : step === 1 && isCreatingBot
                ? "Creating..."
                : "Next Step"}{" "}
            <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
