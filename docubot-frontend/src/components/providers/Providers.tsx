"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { GoogleOAuthProvider } from "@react-oauth/google";

// Mock data structures
export interface MockChatbot {
  id: string;
  name: string;
  goal: string;
  status: "Active" | "Inactive";
  chats: number;
  docs: number;
  plan: "Free" | "Pro" | "Enterprise";
  created: string;
  color: string;
  tone: string;
  description?: string;
  welcomeMessage?: string;
  avatarEmoji?: string;
  systemPrompt?: string;
  llmProvider?: string;
  selectedModel?: string;
  apiKey?: string;
  updated_at?: string;
  deployment_status?: string;
}

const INITIAL_BOTS: MockChatbot[] = [];

const INITIAL_FILES: FileItem[] = [
  {
    id: "doc-1",
    name: "product_manual_v4.pdf",
    size: "2.4 MB",
    type: "PDF",
    uploadedAt: "2026-07-02",
    botIds: ["bot-1"],
    coverage: "94%",
    status: "Ready",
  },
  {
    id: "doc-2",
    name: "faq_docs.docx",
    size: "1.1 MB",
    type: "DOCX",
    uploadedAt: "2026-07-01",
    botIds: ["bot-1"],
    coverage: "88%",
    status: "Ready",
  },
  {
    id: "doc-3",
    name: "acme.com/support/*",
    size: "Web Page",
    type: "URL",
    uploadedAt: "2026-07-02",
    botIds: ["bot-1"],
    coverage: "91%",
    status: "Syncing",
  },
];

// ----------------------------------------------------
// 1. Theme Context
// ----------------------------------------------------
interface ThemeContextType {
  isDarkTheme: boolean;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within a ThemeProvider");
  return context;
}

// ----------------------------------------------------
interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string | null;
  password_last_changed?: string | null;
}

interface AuthContextType {
  isLoggedIn: boolean;
  loading: boolean;
  user: User | null;
  handleLogout: () => void | Promise<void>;
  setLoggedIn: (val: boolean) => void;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}

// ----------------------------------------------------
// 3. Workspace Context
// ----------------------------------------------------
export interface FileItem {
  id: string;
  name: string;
  size: string;
  type: string;
  uploadedAt: string;
  botIds: string[]; // chatbots utilizing this document
  coverage: string;
  status: "Ready" | "Syncing";
}

interface ConfettiPiece {
  id: number;
  left: number;
  color: string;
  delay: number;
  scale: number;
}

interface ChatMessage {
  sender: "user" | "bot";
  text: string;
  time: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug?: string;
  [key: string]: any;
}

interface WorkspaceContextType {
  sidebarOpen: boolean;
  setSidebarOpen: (val: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (val: boolean) => void;
  chatbots: MockChatbot[];
  setChatbots: React.Dispatch<React.SetStateAction<MockChatbot[]>>;
  hasDeployed: boolean;
  setHasDeployed: (val: boolean) => void;

  workspaces: Workspace[];
  setWorkspaces: React.Dispatch<React.SetStateAction<Workspace[]>>;

  // Tenant / Routing derived variables & helper functions
  workspaceId: string;
  currentChatbot: MockChatbot;
  changeCurrentChatbot: (botId: string) => void;

  // Wizard identity states
  wizardStep: number;
  setWizardStep: (step: number) => void;
  newBotName: string;
  setNewBotName: (val: string) => void;
  newBotDesc: string;
  setNewBotDesc: (val: string) => void;
  newBotGoal: string;
  setNewBotGoal: (val: string) => void;
  newBotTone: string;
  setNewBotTone: (val: string) => void;
  newBotColor: string;
  setNewBotColor: (val: string) => void;
  selectedModel: string;
  setSelectedModel: (val: string) => void;

  // Knowledge base states
  uploadedFiles: FileItem[];
  setUploadedFiles: React.Dispatch<React.SetStateAction<FileItem[]>>;
  isTraining: boolean;
  setIsTraining: (val: boolean) => void;
  trainingProgress: number;
  setTrainingProgress: (val: number) => void;
  isTrained: boolean;
  setIsTrained: (val: boolean) => void;
  uploadMethod: "file" | "url";
  setUploadMethod: (val: "file" | "url") => void;
  inputUrl: string;
  setInputUrl: (val: string) => void;

  // Playgrounds managed by usePlayground hook now

  // Payment/Checkout
  selectedPlan: "starter" | "pro" | "enterprise";
  setSelectedPlan: (val: "starter" | "pro" | "enterprise") => void;
  cardName: string;
  setCardName: (val: string) => void;
  cardNumber: string;
  setCardNumber: (val: string) => void;
  cardExpiry: string;
  setCardExpiry: (val: string) => void;
  cardCvv: string;
  setCardCvv: (val: string) => void;
  isPaying: boolean;
  setIsPaying: (val: boolean) => void;
  paymentSuccess: boolean;
  setPaymentSuccess: (val: boolean) => void;

  // Confetti & Helpers
  confetti: ConfettiPiece[];
  embedCodeCopied: boolean;
  startTraining: () => void;
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleUrlSubmit: (e: React.FormEvent) => void;
  removeFile: (id: string) => void;
  handlePayment: (e: React.FormEvent) => void;
  generateConfetti: () => void;
  getIframeCode: () => string;
  copyEmbedCode: () => void;
  resetWizard: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(
  undefined,
);

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context)
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  return context;
}

// ----------------------------------------------------
// Providers Component
// ----------------------------------------------------
export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  // Theme state
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  const toggleTheme = () => {
    const root = document.documentElement;
    if (isDarkTheme) {
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
      root.style.colorScheme = "light";
      setIsDarkTheme(false);
    } else {
      root.classList.add("dark");
      root.removeAttribute("data-theme");
      root.style.colorScheme = "dark";
      setIsDarkTheme(true);
    }
  };

  // Auth state
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);

  // Workspace Creation Modal state
  const [showWorkspacePrompt, setShowWorkspacePrompt] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);

  // Workspace states
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatbots, setChatbots] = useState<MockChatbot[]>(INITIAL_BOTS);
  const [hasDeployed, setHasDeployed] = useState(false);

  // Workspaces state
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);

  // Dynamic Workspace and Chatbot context parsing
  const segments = pathname ? pathname.split("/") : [];
  const urlWorkspaceId = segments[2];
  const workspaceId =
    urlWorkspaceId || (workspaces.length > 0 ? workspaces[0].id : "");

  // Find current chatbot based on URL
  const botIdFromUrl =
    segments[3] === "bots" && segments[4] !== "new" ? segments[4] : undefined;

  // Track selected chatbot fallback in state if not on a bot-specific route
  const [selectedBotIdState, setSelectedBotIdState] = useState<string>("bot-1");

  // Keep state in sync with URL if URL changes
  useEffect(() => {
    if (botIdFromUrl) {
      setSelectedBotIdState(botIdFromUrl);
    }
  }, [botIdFromUrl]);

  const activeBotId = botIdFromUrl || selectedBotIdState;
  const currentChatbot =
    chatbots.find((b) => b.id === activeBotId) ||
    chatbots[0] ||
    INITIAL_BOTS[0];

  const changeCurrentChatbot = useCallback(
    (newBotId: string) => {
      setSelectedBotIdState(newBotId);

      // Check if we are on a bot-specific route: /dashboard/[workspaceId]/bots/[botId]/[subpage]
      if (
        segments.length >= 5 &&
        segments[1] === "dashboard" &&
        segments[3] === "bots" &&
        segments[4] !== "new"
      ) {
        const newSegments = [...segments];
        newSegments[4] = newBotId;
        router.push(newSegments.join("/"));
      }
    },
    [segments, router],
  );

  // Wizard identity states
  const [wizardStep, setWizardStep] = useState(1);
  const [newBotName, setNewBotName] = useState("");
  const [newBotDesc, setNewBotDesc] = useState("");
  const [newBotGoal, setNewBotGoal] = useState("Support");
  const [newBotTone, setNewBotTone] = useState("Professional");
  const [newBotColor, setNewBotColor] = useState("#0052ff");
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");

  // Knowledge base states
  const [uploadedFiles, setUploadedFiles] = useState<FileItem[]>(INITIAL_FILES);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [isTrained, setIsTrained] = useState(false);
  const [uploadMethod, setUploadMethod] = useState<"file" | "url">("file");
  const [inputUrl, setInputUrl] = useState("");

  // Payment/Checkout
  const [selectedPlan, setSelectedPlan] = useState<
    "starter" | "pro" | "enterprise"
  >("starter");
  const [cardName, setCardName] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvv, setCardCvv] = useState("");
  const [isPaying, setIsPaying] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  // Confetti particles
  const [confetti, setConfetti] = useState<ConfettiPiece[]>([]);
  const [embedCodeCopied, setEmbedCodeCopied] = useState(false);

  // Sync login status and load data
  useEffect(() => {
    const checkAuthAndLoadData = async () => {
      const logged = localStorage.getItem("isLoggedIn") === "true";
      const deployed = localStorage.getItem("hasDeployed") === "true";

      if (deployed) {
        setHasDeployed(true);
      }

      setIsLoggedIn(logged);

      if (logged) {
        try {
          // 1. Verify Auth (always do this if logged is true in localStorage)
          const authRes = await fetchApi("/auth/me");
          if (!authRes.ok) throw new Error("Auth failed");
          const authData = await authRes.json();
          setUser(authData);

          if (pathname && pathname.startsWith("/dashboard")) {
            // 2. Fetch Workspaces
            const wsRes = await fetchApi("/workspaces");
            if (wsRes.ok) {
              const wsData = await wsRes.json();
              setWorkspaces(wsData);
              if (wsData.length === 0) {
                setShowWorkspacePrompt(true);
              } else if (pathname === "/dashboard") {
                router.replace(`/dashboard/${wsData[0].id}`);
              }

              // 3. Fetch Chatbots for the current workspace
              const currentWsId =
                urlWorkspaceId || (wsData.length > 0 ? wsData[0].id : null);
              if (currentWsId) {
                const botsRes = await fetchApi(
                  `/workspaces/${currentWsId}/chatbots`,
                );
                if (botsRes.ok) {
                  const botsData = await botsRes.json();

                  // Fetch stats for all bots concurrently
                  const botsWithStats = await Promise.all(
                    botsData.map(async (b: any) => {
                      let docsCount = 0;
                      try {
                        const statsRes = await fetchApi(
                          `/workspaces/${currentWsId}/chatbots/${b.id}/knowledge-base/stats`,
                        );
                        if (statsRes.ok) {
                          const statsData = await statsRes.json();
                          docsCount = statsData.total_documents || 0;
                        }
                      } catch (e) {
                        console.error("Failed to fetch bot stats", e);
                      }

                      return {
                        id: b.id,
                        name: b.name,
                        goal: "Support",
                        status: (b.is_active && b.deployment_status === "published" && docsCount > 0) ? "Active" : "Inactive",
                        chats: b.total_conversations || 0,
                        docs: docsCount,
                        plan: "Free",
                        created: b.created_at,
                        updated_at: b.updated_at,
                        deployment_status: b.deployment_status,
                        color: b.brand_color || "#0052ff",
                        tone: b.tone_preset
                          ? b.tone_preset.charAt(0).toUpperCase() +
                            b.tone_preset.slice(1).toLowerCase()
                          : "Friendly",
                        systemPrompt: b.custom_system_prompt,
                        selectedModel: b.llm_model,
                        llmProvider: b.llm_provider
                          ? b.llm_provider.toLowerCase() === "openai"
                            ? "OpenAI"
                            : b.llm_provider.charAt(0).toUpperCase() +
                              b.llm_provider.slice(1).toLowerCase()
                          : "OpenAI",
                        welcomeMessage: b.welcome_message,
                        apiKey: b.custom_api_key_masked,
                      };
                    }),
                  );

                  setChatbots(botsWithStats);
                }
              }
            }
          }
        } catch (err: any) {
          console.error("Failed to load initial data", err);
          if (err.message === "Auth failed") {
            handleLogout();
          }
        } finally {
          setLoading(false);
        }
      } else {
        if (pathname && pathname.startsWith("/dashboard")) {
          router.push("/");
        }
        setLoading(false);
      }
    };

    checkAuthAndLoadData();

    // Sync dark theme
    setIsDarkTheme(document.documentElement.classList.contains("dark"));
  }, [router, pathname]);

  const handleLogout = async () => {
    try {
      await fetchApi("/auth/logout", { method: "POST" });
    } catch (err) {
      console.error("Logout API call failed", err);
    }
    localStorage.removeItem("isLoggedIn");
    sessionStorage.removeItem("dismissedWhatsNew");
    setIsLoggedIn(false);
    setLoading(true);
    router.push("/");
    window.dispatchEvent(new Event("storage"));
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setIsCreatingWorkspace(true);
    try {
      const res = await fetchApi("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: newWorkspaceName }),
      });
      if (res.ok) {
        const newWs = await res.json();
        setWorkspaces([newWs]);
        setShowWorkspacePrompt(false);
        router.push(`/dashboard/${newWs.id}`);
      }
    } catch (err) {
      console.error("Failed to create workspace", err);
    } finally {
      setIsCreatingWorkspace(false);
    }
  };

  const setLoggedIn = (val: boolean) => {
    setIsLoggedIn(val);
    if (val) {
      localStorage.setItem("isLoggedIn", "true");
      setLoading(true);
      router.push("/dashboard");
    } else {
      localStorage.removeItem("isLoggedIn");
    }
  };

  // Helper actions
  const startTraining = () => {
    if (uploadedFiles.length === 0) {
      alert("Please upload at least one document to train your chatbot.");
      return;
    }
    setIsTraining(true);
    setTrainingProgress(0);
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isTraining) {
      interval = setInterval(() => {
        setTrainingProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            setIsTraining(false);
            setIsTrained(true);
            setTimeout(() => {
              if (pathname && pathname.includes("/bots/new")) {
                setWizardStep(3); // Auto proceed to playground testing in wizard
              } else {
                // Redirect to Bot Studio (Settings)
                router.push(
                  `/dashboard/${workspaceId}/bots/${activeBotId}/settings`,
                );
              }
            }, 600);
            return 100;
          }
          return prev + 10;
        });
      }, 250);
    }
    return () => clearInterval(interval);
  }, [isTraining, pathname, router, workspaceId, activeBotId]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const maxFreeSize = 5 * 1024 * 1024; // 5 MB in bytes
      const filesArr = Array.from(e.target.files);

      // Filter out files that exceed 5MB
      const oversizedFiles = filesArr.filter((file) => file.size > maxFreeSize);
      if (oversizedFiles.length > 0) {
        alert(
          `Under the Free Trial plan, documents must be below 5 MB.\n` +
            `The following file(s) exceed this limit:\n` +
            oversizedFiles
              .map(
                (file) =>
                  `- ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
              )
              .join("\n"),
        );
        return;
      }

      const formattedFiles = filesArr.map((file) => ({
        id: `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        name: file.name,
        size: (file.size / 1024 / 1024).toFixed(2) + " MB",
        type: file.name.split(".").pop()?.toUpperCase() || "PDF",
        uploadedAt: new Date().toISOString().split("T")[0],
        botIds: [botIdFromUrl || "new-bot-temp"],
        coverage: "92%",
        status: "Ready" as const,
      }));
      setUploadedFiles((prev) => [...prev, ...formattedFiles]);
    }
  };

  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;

    let urlToVerify = inputUrl.trim();
    if (!/^https?:\/\//i.test(urlToVerify)) {
      urlToVerify = "https://" + urlToVerify;
    }

    try {
      new URL(urlToVerify);
    } catch (_) {
      alert("Please enter a valid URL (e.g., https://example.com/docs).");
      return;
    }

    const targetBotId = botIdFromUrl || "new-bot-temp";

    const newUrlItem = {
      id: `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: urlToVerify,
      size: "Web Page",
      type: "URL",
      uploadedAt: new Date().toISOString().split("T")[0],
      botIds: [targetBotId],
      coverage: "91%",
      status: "Syncing" as const,
    };

    if (
      uploadedFiles.some(
        (f) =>
          f.name.toLowerCase() === urlToVerify.toLowerCase() &&
          f.botIds.includes(targetBotId),
      )
    ) {
      alert("This URL has already been added for this chatbot.");
      return;
    }

    setUploadedFiles((prev) => [...prev, newUrlItem]);
    setInputUrl("");
  };

  const removeFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((file) => file.id !== id));
    if (uploadedFiles.length <= 1) {
      setIsTrained(false);
    }
  };

  const handlePayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cardName || !cardNumber || !cardExpiry || !cardCvv) {
      alert("Please enter credit card info.");
      return;
    }
    setIsPaying(true);

    setTimeout(() => {
      setIsPaying(false);
      setPaymentSuccess(true);

      const newBotId = `bot-${Date.now()}`;
      const newlyCreatedBot: MockChatbot = {
        id: newBotId,
        name: newBotName || "Support Assistant",
        goal:
          newBotGoal === "Support"
            ? "Customer Support"
            : newBotGoal === "Leads"
              ? "Lead Generation"
              : "E-commerce Help",
        status: "Active",
        chats: 0,
        docs: uploadedFiles.filter((f) => f.botIds.includes("new-bot-temp"))
          .length,
        plan:
          selectedPlan === "starter"
            ? "Free"
            : selectedPlan === "pro"
              ? "Pro"
              : "Enterprise",
        created: new Date().toISOString().split("T")[0],
        color: newBotColor,
        tone: newBotTone,
      };

      // Map temp files to the actual newly created chatbot ID
      setUploadedFiles((prev) =>
        prev.map((file) =>
          file.botIds.includes("new-bot-temp")
            ? { ...file, botIds: [newBotId] }
            : file,
        ),
      );

      setChatbots((prev) => [newlyCreatedBot, ...prev]);
      setHasDeployed(true);
      localStorage.setItem("hasDeployed", "true");
      generateConfetti();
      setWizardStep(6);
    }, 1500);
  };

  const generateConfetti = () => {
    const colors = ["#0052ff", "#10B981", "#EC4899", "#8B5CF6", "#F59E0B"];
    const pieces = Array.from({ length: 60 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      color: colors[Math.floor(Math.random() * colors.length)],
      delay: Math.random() * 1.5,
      scale: 0.5 + Math.random() * 0.8,
    }));
    setConfetti(pieces);
  };

  const getIframeCode = () => {
    const botId =
      newBotName.toLowerCase().replace(/\s+/g, "-") || "assistant-bot";
    return `<script \n  src="https://cdn.docubot.ai/widget.js" \n  data-bot-id="${botId}" \n  data-theme-color="${newBotColor}">\n</script>`;
  };

  const copyEmbedCode = () => {
    navigator.clipboard.writeText(getIframeCode());
    setEmbedCodeCopied(true);
    setTimeout(() => setEmbedCodeCopied(false), 2000);
  };

  const resetWizard = () => {
    setWizardStep(1);
    setNewBotName("");
    setNewBotDesc("");
    // Filter out temporary files uploaded during wizard creation
    setUploadedFiles((prev) =>
      prev.filter((f) => !f.botIds.includes("new-bot-temp")),
    );
    setIsTrained(false);
    setCardName("");
    setCardNumber("");
    setCardExpiry("");
    setCardCvv("");
    setUploadMethod("file");
    setInputUrl("");
    router.push(`/dashboard/${workspaceId}`);
  };

  const workspaceValue = useMemo(
    () => ({
      sidebarOpen,
      setSidebarOpen,
      sidebarCollapsed,
      setSidebarCollapsed,
      chatbots,
      setChatbots,
      hasDeployed,
      setHasDeployed,
      workspaces,
      setWorkspaces,

      workspaceId,
      currentChatbot,
      changeCurrentChatbot,

      wizardStep,
      setWizardStep,
      newBotName,
      setNewBotName,
      newBotDesc,
      setNewBotDesc,
      newBotGoal,
      setNewBotGoal,
      newBotTone,
      setNewBotTone,
      newBotColor,
      setNewBotColor,
      selectedModel,
      setSelectedModel,

      uploadedFiles,
      setUploadedFiles,
      isTraining,
      setIsTraining,
      trainingProgress,
      setTrainingProgress,
      isTrained,
      setIsTrained,
      uploadMethod,
      setUploadMethod,
      inputUrl,
      setInputUrl,

      selectedPlan,
      setSelectedPlan,
      cardName,
      setCardName,
      cardNumber,
      setCardNumber,
      cardExpiry,
      setCardExpiry,
      cardCvv,
      setCardCvv,
      isPaying,
      setIsPaying,
      paymentSuccess,
      setPaymentSuccess,

      confetti,
      embedCodeCopied,
      startTraining,
      handleFileUpload,
      handleUrlSubmit,
      removeFile,
      handlePayment,
      generateConfetti,
      getIframeCode,
      copyEmbedCode,
      resetWizard,
    }),
    [
      sidebarOpen,
      sidebarCollapsed,
      chatbots,
      hasDeployed,
      workspaces,
      workspaceId,
      currentChatbot,
      changeCurrentChatbot,
      wizardStep,
      newBotName,
      newBotDesc,
      newBotGoal,
      newBotTone,
      newBotColor,
      selectedModel,
      uploadedFiles,
      isTraining,
      trainingProgress,
      isTrained,
      uploadMethod,
      inputUrl,
      selectedPlan,
      cardName,
      cardNumber,
      cardExpiry,
      cardCvv,
      isPaying,
      paymentSuccess,
      confetti,
      embedCodeCopied,
    ],
  );

  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ""}>
      <ThemeContext.Provider value={{ isDarkTheme, toggleTheme }}>
        <AuthContext.Provider
          value={{
            isLoggedIn,
            loading,
            user,
            handleLogout,
            setLoggedIn,
            setUser,
          }}
        >
        <WorkspaceContext.Provider value={workspaceValue}>
          {showWorkspacePrompt && (
            <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
              <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-2xl max-w-md w-full border border-slate-200 dark:border-slate-800">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                  Create Your First Workspace
                </h2>
                <p className="text-sm text-slate-500 mb-6">
                  You need a workspace to start creating chatbots.
                </p>
                <form onSubmit={handleCreateWorkspace}>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      Workspace Name
                    </label>
                    <input
                      type="text"
                      required
                      value={newWorkspaceName}
                      onChange={(e) => setNewWorkspaceName(e.target.value)}
                      placeholder="e.g. My Startup"
                      className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0052ff] dark:text-white"
                    />
                  </div>
                  <button
                    disabled={isCreatingWorkspace || !newWorkspaceName.trim()}
                    type="submit"
                    className="w-full bg-[#0052ff] hover:bg-[#003ecc] text-white py-2.5 rounded-xl font-semibold shadow-md disabled:opacity-70 transition-all"
                  >
                    {isCreatingWorkspace ? "Creating..." : "Create Workspace"}
                  </button>
                </form>
              </div>
            </div>
          )}
          {children}
        </WorkspaceContext.Provider>
      </AuthContext.Provider>
    </ThemeContext.Provider>
    </GoogleOAuthProvider>
  );
}
