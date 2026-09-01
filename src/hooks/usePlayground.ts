import { useState, useEffect, useCallback, useRef } from "react";
import { useWebSocket } from "./useWebSocket";
import { fetchApi } from "@/lib/api";

export interface ChatMessage {
  sender: "user" | "bot";
  text: string;
  time: string;
}

export interface PlaygroundWsPayload {
  type?: string;
  detail?: string;
  message?: string;
  content?: string;
  role?: "user" | "bot";
  created_at?: string;
}

export function usePlayground(workspaceId?: string, chatbotId?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [wsUrl, setWsUrl] = useState<string | null>(null);
  const initialized = useRef<string | null>(null);

  // Derive base URL from env or use default localhost
  const getBaseWsUrl = () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";
    return apiBase.replace(/^http/, "ws");
  };

  // Initialize Session
  useEffect(() => {
    if (!workspaceId || !chatbotId || chatbotId === "bot-1" || initialized.current === chatbotId) return;
    
    setMessages([]);
    setError(null);

    const initSession = async () => {
      initialized.current = chatbotId;
      try {
        const storageKey = `docubot_playground_${chatbotId}`;
        const cached = sessionStorage.getItem(storageKey);
        let tokenToUse: string | null = null;
        let sessionIdToUse: string | null = null;

        if (cached) {
          const parsed = JSON.parse(cached);
          tokenToUse = parsed.token;
          sessionIdToUse = parsed.sessionId;
        }

        // If no valid session, create a new one
        if (!tokenToUse) {
          const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${chatbotId}/playground/session`, {
            method: "POST",
            body: JSON.stringify({})
          });

          if (!res.ok) throw new Error("Failed to create playground session");
          const data = await res.json();
          tokenToUse = data.session_token;
          sessionIdToUse = data.id;

          sessionStorage.setItem(storageKey, JSON.stringify({ token: tokenToUse, sessionId: sessionIdToUse }));
        }

        setWsUrl(`${getBaseWsUrl()}/workspaces/${workspaceId}/chatbots/${chatbotId}/playground/chat?token=${tokenToUse}`);

        // Fetch existing messages if resuming
        if (sessionIdToUse && tokenToUse) {
          const msgsRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${chatbotId}/playground/session/${sessionIdToUse}/messages?token=${tokenToUse}`);
          
          if (msgsRes.ok) {
            const data = await msgsRes.json();
            if (data.messages) {
              const history: ChatMessage[] = data.messages.map((m: { role: "user" | "bot"; content: string; created_at: string }) => ({
                sender: m.role,
                text: m.content,
                time: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }));
              setMessages(history);
            }
          }
        }
      } catch (err: unknown) {
        console.error("Playground Init Error:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize playground");
      }
    };

    initSession();
  }, [workspaceId, chatbotId]);

  // WebSocket Handlers
  const handleMessage = useCallback((data: PlaygroundWsPayload) => {
    setIsTyping(false);
    
    // Check for playground specific errors
    if (data.detail) {
      setError(data.detail); // e.g. "Playground query limit reached."
      return;
    }
    
    if (data.type === "error") {
      setError(data.message || "An error occurred");
      return;
    }

    if (data.type === "message" || data.type === "response" || data.message) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: data.content || data.message || "",
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  }, []);

  const { status, send } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    onError: () => {
      setIsTyping(false);
      setError("WebSocket connection error.");
    }
  });

  const sendMessage = useCallback((text: string) => {
    if (!text.trim()) return;
    setError(null);
    setMessages((prev) => [
      ...prev,
      {
        sender: "user",
        text,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
    setIsTyping(true);
    send({ type: "message", content: text });
  }, [send]);

  const regenerateLastMessage = useCallback(() => {
    const userMsgs = messages.filter((m) => m.sender === "user");
    if (userMsgs.length > 0) {
      sendMessage(userMsgs[userMsgs.length - 1].text);
    }
  }, [messages, sendMessage]);

  return {
    messages,
    isTyping,
    connectionStatus: status,
    error,
    sendMessage,
    regenerateLastMessage
  };
}
