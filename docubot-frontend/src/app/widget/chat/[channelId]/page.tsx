'use client';

import React, { useState, useEffect, useRef, use } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, X, AlertTriangle, ShieldAlert, Loader2, ArrowUpRight } from 'lucide-react';

interface Source {
  title: string;
  url: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
  error?: boolean;
}

// Simple safe markdown formatting component
function FormattedMessage({ text }: { text: string }) {
  const lines = text.split('\n');
  
  return (
    <div className="space-y-1.5 text-[14px] leading-relaxed">
      {lines.map((line, lineIdx) => {
        // Bullet list check
        const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ');
        const isNumbered = /^\d+\.\s/.test(line.trim());
        
        let content = line;
        if (isBullet) content = line.trim().substring(2);
        if (isNumbered) content = line.trim().replace(/^\d+\.\s/, '');

        // Format bold text (**text**)
        const parts = content.split('**');
        const formattedContent = parts.map((part, partIdx) => {
          if (partIdx % 2 === 1) {
            return <strong key={partIdx} className="font-semibold text-current">{part}</strong>;
          }
          return part;
        });

        if (isBullet) {
          return (
            <ul key={lineIdx} className="list-disc pl-4 my-1">
              <li>{formattedContent}</li>
            </ul>
          );
        }

        if (isNumbered) {
          const num = line.trim().match(/^(\d+)\.\s/)?.[1] || '1';
          return (
            <ol key={lineIdx} className="list-decimal pl-4 my-1" start={parseInt(num)}>
              <li>{formattedContent}</li>
            </ol>
          );
        }

        return <p key={lineIdx}>{formattedContent}</p>;
      })}
    </div>
  );
}

export default function ChatWidgetPage({ params }: { params: Promise<{ channelId: string }> }) {
  const { channelId: _channelId } = use(params);
  const searchParams = useSearchParams();
  
  const paramTheme = searchParams.get('theme') || 'light';
  const parentOrigin = searchParams.get('origin') || '';
  const workspaceSlug = searchParams.get('workspace') || '';
  const chatbotId = searchParams.get('chatbot') || '';

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (paramTheme === 'dark') return 'dark';
    if (paramTheme === 'auto' && typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });
  const [errorState, setErrorState] = useState<{ type: 400 | 403 | 429 | 500; message: string } | null>(null);
  const [brandColor, setBrandColor] = useState('#0052ff');
  const [chatbotName, setChatbotName] = useState('DocuBot Assistant');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Sync theme
  useEffect(() => {
    if (paramTheme === 'dark') {
      setTheme('dark');
    } else if (paramTheme === 'auto' && typeof window !== 'undefined') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
    } else {
      setTheme('light');
    }
  }, [paramTheme]);

  // Initial session creation
  useEffect(() => {
    const initSession = async () => {
      if (!workspaceSlug || !chatbotId) {
        setErrorState({ type: 500, message: "Missing workspace or chatbot configuration." });
        return;
      }

      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
        const storageKey = `docubot_session_id_${workspaceSlug}_${chatbotId}`;
        const existingSessionId = typeof window !== 'undefined' ? localStorage.getItem(storageKey) : null;

        const res = await fetch(`${backendUrl}/api/v1/chatbot/${workspaceSlug}/${chatbotId}/session`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Simulated-Origin': parentOrigin,
          },
          body: JSON.stringify({ existing_session_id: existingSessionId || undefined }),
        });

        if (res.status === 403) {
          const errorData = await res.json();
          setErrorState({ type: 403, message: errorData.message || 'Domain forbidden: Unauthorized access.' });
          return;
        }

        if (res.status === 400) {
          const errorData = await res.json();
          const detail = errorData.detail;
          const isOffline = 
            errorData.error_code === "BOT_OFFLINE" || 
            (detail && typeof detail === 'object' && detail.error_code === "BOT_OFFLINE") ||
            (typeof detail === 'string' && (detail.includes("Bot is offline") || detail.includes("not currently available")));

          if (isOffline) {
            setErrorState({ type: 400, message: 'Bot is offline' });
            return;
          }
        }

        if (!res.ok) throw new Error('Failed to create session');
        
        const data = await res.json();
        if (typeof window !== 'undefined' && data.id) {
          localStorage.setItem(storageKey, data.id);
        }
        setSessionToken(data.session_token);
        
        if (data.brand_color) {
          setBrandColor(data.brand_color);
          if (typeof window !== 'undefined' && window.parent) {
            window.parent.postMessage({ type: 'docubot-brand-color', color: data.brand_color }, '*');
          }
        }
        if (data.chatbot_name) {
          setChatbotName(data.chatbot_name);
        }

        let loadedHistory = false;
        try {
          const historyRes = await fetch(`${backendUrl}/api/v1/chatbot/${workspaceSlug}/${chatbotId}/session/${data.id}/messages?token=${data.session_token}&limit=50`, {
            headers: { 'X-Simulated-Origin': parentOrigin },
          });
          if (historyRes.ok) {
            const historyData = await historyRes.json();
            if (historyData.messages && historyData.messages.length > 0) {
              const formattedMessages: Message[] = historyData.messages.map((msg: any) => ({
                id: msg.id || Math.random().toString(),
                role: msg.role === 'user' ? 'user' : 'assistant',
                content: msg.content || '',
                timestamp: new Date(msg.created_at || Date.now()),
                sources: Array.isArray(msg.sources) ? msg.sources : undefined,
              }));
              setMessages(formattedMessages);
              loadedHistory = true;
            }
          }
        } catch (historyErr) {
          console.error("Failed to load history:", historyErr);
        }

        // Initial welcome message if no prior chat history exists
        if (!loadedHistory) {
          setMessages([
            {
              id: 'welcome',
              role: 'assistant',
              content: data.welcome_message || 'Hello! I am your **SYNQDOC** assistant. How can I help you today?',
              timestamp: new Date(),
            },
          ]);
        }
        
      } catch (err) {
        console.error("Session init error:", err);
        setErrorState({ type: 500, message: 'Could not connect to the backend server. Please try again.' });
      }
    };
    
    initSession();
  }, [workspaceSlug, chatbotId, parentOrigin]);

  // WebSocket Connection
  useEffect(() => {
    if (!sessionToken || !workspaceSlug || !chatbotId) return;

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
    const wsUrl = backendUrl.replace(/^http/, 'ws') + `/api/v1/chatbot/${workspaceSlug}/${chatbotId}/chat?token=${sessionToken}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setErrorState(null);
    };

    ws.onmessage = (event) => {
      setIsTyping(false);
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'error') {
          setMessages(prev => [...prev, {
            id: Math.random().toString(36).substring(7),
            role: 'assistant',
            content: data.message || 'An error occurred.',
            timestamp: new Date(),
            error: true
          }]);
        } else if (data.type === 'response') {
          setMessages(prev => [...prev, {
            id: Math.random().toString(36).substring(7),
            role: 'assistant',
            content: data.content || data.clarification_question || '',
            timestamp: new Date(),
            sources: data.sources
          }]);
        }
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setIsConnected(false);
      setIsTyping(false);
    };

    return () => {
      ws.close();
    };
  }, [sessionToken, workspaceSlug, chatbotId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async (e?: React.FormEvent, customText?: string) => {
    if (e) e.preventDefault();
    const textToSend = customText !== undefined ? customText : input;
    if (!textToSend.trim()) return;

    if (!isConnected || !wsRef.current) {
       setErrorState({ type: 500, message: "Disconnected from server. Please wait or reload." });
       return;
    }

    if (customText === undefined) setInput('');

    // Add User Message
    const userMsgId = Math.random().toString(36).substring(7);
    const userMsg: Message = {
      id: userMsgId,
      role: 'user',
      content: textToSend,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      wsRef.current.send(JSON.stringify({ type: 'message', content: textToSend }));
    } catch (err) {
      console.error('Error sending message:', err);
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(7),
          role: 'assistant',
          content: 'Error: Connection lost. Please check your connection.',
          timestamp: new Date(),
          error: true,
        },
      ]);
    }
  };

  // Close widget action
  const handleClose = () => {
    window.parent.postMessage({ type: 'docubot-close' }, '*');
  };

  return (
    <div className={`h-screen flex flex-col font-sans transition-colors duration-300 ${theme === 'dark' ? 'bg-[#0B132B] text-slate-100' : 'bg-white text-slate-800'}`}>
      
      {/* Widget Header */}
      <div 
        style={{ backgroundColor: brandColor }}
        className="px-4 py-3 flex items-center justify-between border-b border-black/10 text-white transition-colors duration-300"
      >
        <div className="flex items-center space-x-2">
          {/* Pulsing Status Dot */}
          <div className="relative flex h-2.5 w-2.5">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${isConnected ? 'bg-emerald-300 animate-ping' : (errorState?.type === 400 ? 'bg-slate-400' : 'bg-amber-300')}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isConnected ? 'bg-emerald-400' : (errorState?.type === 400 ? 'bg-slate-500' : 'bg-amber-400')}`}></span>
          </div>
          <div>
            <h3 className="text-sm font-semibold tracking-wide font-display">{chatbotName}</h3>
            <p className={`text-[10px] font-medium ${isConnected ? 'text-emerald-200' : (errorState?.type === 400 ? 'text-slate-300' : 'text-amber-200')}`}>{isConnected ? 'Online' : (errorState?.type === 400 ? 'Offline' : 'Connecting...')}</p>
          </div>
        </div>
        
        {/* Close Button */}
        <button 
          onClick={handleClose}
          className="p-1.5 rounded-lg transition-all duration-200 hover:bg-white/10 text-white/80 hover:text-white border-0 bg-transparent cursor-pointer"
          aria-label="Close chat"
        >
          <X size={16} />
        </button>
      </div>

      {/* Security Whitelist Status Banner (Only visible if 403 or 429) */}
      {errorState && errorState.type !== 400 && (
        <div className={`flex items-start space-x-2 px-4 py-2.5 text-xs ${
          errorState.type === 403 
            ? 'bg-rose-50 text-rose-800 border-b border-rose-100 dark:bg-rose-950/40 dark:text-rose-200 dark:border-rose-900/50' 
            : 'bg-amber-50 text-amber-800 border-b border-amber-100 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-900/50'
        }`}>
          {errorState.type === 403 ? <ShieldAlert className="shrink-0 mt-0.5" size={14} /> : <AlertTriangle className="shrink-0 mt-0.5" size={14} />}
          <div className="flex-1 font-medium">{errorState.message}</div>
        </div>
      )}
      
      {errorState?.type === 400 && (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-500 space-y-3">
          <div className="w-12 h-12 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
            <X size={24} className="text-slate-400" />
          </div>
          <p className="text-sm">This chatbot is currently offline or unpublished and cannot accept messages right now.</p>
        </div>
      )}

      {/* Messages Stream */}
      {(!errorState || errorState.type !== 400) && (
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div 
              key={msg.id}
              className={`flex flex-col max-w-[85%] animate-fade-in ${
                isUser ? 'ml-auto items-end' : 'mr-auto items-start'
              }`}
            >
              {/* Message Bubble */}
              <div 
                style={isUser ? { background: brandColor } : undefined}
                className={`px-4 py-3 rounded-2xl ${
                  isUser 
                    ? 'text-white rounded-br-none shadow-sm'
                    : msg.error 
                      ? 'bg-rose-50 text-rose-900 border border-rose-200 rounded-bl-none dark:bg-rose-950/20 dark:text-rose-100 dark:border-rose-900'
                      : theme === 'dark'
                        ? 'bg-[#1C2541] border border-slate-800 text-slate-100 rounded-bl-none'
                        : 'bg-slate-50 border border-slate-100 text-slate-800 rounded-bl-none'
                }`}
              >
                <FormattedMessage text={msg.content} />
              </div>


              {/* Timestamp */}
              <span className="text-[10px] text-slate-400 mt-1 px-1">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          );
        })}

        {/* Typing Loader */}
        {isTyping && (
          <div className="flex flex-col max-w-[85%] mr-auto items-start">
            <div className={`px-4 py-3 rounded-2xl rounded-bl-none flex items-center space-x-1.5 ${
              theme === 'dark' ? 'bg-[#1C2541] border border-slate-800' : 'bg-slate-50 border border-slate-100'
            }`}>
              <Loader2 className="animate-spin text-blue-500" size={16} />
              <span className="text-xs text-slate-400">SYNQDOC is searching...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
      )}

      {/* Input Box */}
      <form 
        onSubmit={handleSendMessage}
        className={`p-3 border-t flex flex-col space-y-2 ${
          theme === 'dark' ? 'border-slate-800 bg-[#0F172E]' : 'border-slate-100 bg-white'
        }`}
      >
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className={`flex-1 px-4 py-2.5 rounded-xl text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all ${
              theme === 'dark' 
                ? 'bg-[#1C2541] border-slate-800 text-slate-100 placeholder-slate-500 focus:border-slate-700' 
                : 'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:bg-white focus:border-blue-400'
            }`}
            disabled={isTyping || !isConnected}
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping || !isConnected}
            style={{ backgroundColor: brandColor }}
            className="p-2.5 rounded-xl text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm"
          >
            <Send size={16} />
          </button>
        </div>

        {/* Brand Footer */}
        <div className="flex items-center justify-between px-1 text-[10px] text-slate-400">
          <span>{parentOrigin ? `Embedded on: ${parentOrigin.replace(/^https?:\/\//, '')}` : 'Sandbox'}</span>
          <span className="font-medium">Powered by <span className="font-semibold text-blue-500 tracking-wide">DocuBot</span></span>
        </div>
      </form>
    </div>
  );
}
