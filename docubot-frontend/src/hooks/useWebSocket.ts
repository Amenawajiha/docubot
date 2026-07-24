import { useEffect, useRef, useState, useCallback } from "react";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions {
  url: string | null;
  onMessage?: (data: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (event: Event) => void;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
}: UseWebSocketOptions) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const messageQueue = useRef<any[]>([]);

  useEffect(() => {
    if (!url) return;

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      
      // Flush queued messages
      while (messageQueue.current.length > 0) {
        const msg = messageQueue.current.shift();
        ws.send(typeof msg === "string" ? msg : JSON.stringify(msg));
      }
      
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch (err) {
        onMessage?.(event.data);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      onDisconnect?.();
    };

    ws.onerror = (event) => {
      setStatus("error");
      onError?.(event);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [url]);

  const send = useCallback((data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    } else {
      console.warn("WebSocket is not connected yet, queueing message.");
      messageQueue.current.push(data);
    }
  }, []);

  return { status, send };
}
