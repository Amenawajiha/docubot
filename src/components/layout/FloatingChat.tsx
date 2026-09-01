"use client";

import React, { useState, useEffect, useRef } from "react";
import Lottie from "lottie-react";
import { MessageSquare, X, Send, Smile } from "lucide-react";
import { useWorkspace } from "@/components/providers/Providers";

interface Message {
  sender: "user" | "bot";
  text: string;
  time: string;
}

export default function FloatingChat() {
  const { currentChatbot } = useWorkspace();
  const [isOpen, setIsOpen] = useState(false);
  const [animationData, setAnimationData] = useState<any>(null);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load Lottie JSON from public path
  useEffect(() => {
    fetch("/images/INSEE%20AI.json")
      .then((res) => {
        if (!res.ok) throw new Error("Lottie file not found");
        return res.json();
      })
      .then((data) => setAnimationData(data))
      .catch((err) => {
        // Retry with unescaped space just in case
        fetch("/images/bot.json")
          .then((res) => res.json())
          .then((data) => setAnimationData(data))
          .catch((err2) => {
            console.warn("Could not load Lottie animation, using fallback icon.", err2);
          });
      });
  }, []);

  // Sync initial welcome message from active chatbot
  useEffect(() => {
    if (currentChatbot) {
      setMessages([
        {
          sender: "bot",
          text: currentChatbot.welcomeMessage || `Hello! I am ${currentChatbot.name}. How can I assist you today?`,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    }
  }, [currentChatbot]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userText = inputVal;
    setInputVal("");

    setMessages((prev) => [
      ...prev,
      {
        sender: "user",
        text: userText,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      }
    ]);

    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      let botResponse = "";
      const lower = userText.toLowerCase();

      if (lower.includes("hello") || lower.includes("hi")) {
        botResponse = `Hi there! I am ${currentChatbot?.name || "AI Assistant"}. How can I support you today?`;
      } else if (lower.includes("pricing") || lower.includes("plan")) {
        botResponse = "We offer a Starter Tier for $19/mo and a Professional Tier for $49/mo. Let me know if you want details!";
      } else if (lower.includes("docs") || lower.includes("train")) {
        botResponse = `Yes, I am trained on your workspace documents and ready to resolve your requests!`;
      } else {
        botResponse = `I'm analyzing your request: "${userText}". How can I help clarify further?`;
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: botResponse,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
      setIsTyping(false);
    }, 1200);
  };

  return (
    <div className="text-left font-sans">
      {/* Floating Lottie trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-[999] p-0 border-0 bg-transparent cursor-pointer rounded-full transition-all duration-300 hover:scale-[1.08] active:scale-[0.95]"
      >
        {animationData ? (
          <div className="w-16 h-16 flex items-center justify-center relative overflow-hidden">
            <Lottie
              animationData={animationData}
              loop={true}
              style={{ width: 68, height: 68 }}
            />
          </div>
        ) : (
          <div className="w-14 h-14 rounded-full bg-[#0D53FC] hover:bg-[#0a43ca] text-white shadow-2xl flex items-center justify-center relative transition-colors duration-250">
            <MessageSquare className="w-6 h-6" />
          </div>
        )}
      </button>

      {/* Floating Chat Drawer Window */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 w-[310px] max-w-[90vw] h-[420px] z-[998] flex flex-col rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 shadow-2xl overflow-hidden transition-all duration-300 animate-fadeIn">
          {/* Header */}
          <div className="bg-[#0D53FC] text-white px-4 py-3 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <span className="text-lg leading-none">{currentChatbot?.avatarEmoji || "🤖"}</span>
              <div className="space-y-0.5">
                <h4 className="text-[11px] font-bold truncate max-w-[160px]">{currentChatbot?.name || "Assistant"}</h4>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-450 animate-pulse" />
                  <span className="text-[7px] font-bold text-blue-100">Online</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 text-blue-100 hover:text-white bg-white/10 hover:bg-white/20 border-0 rounded-lg cursor-pointer transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages view */}
          <div className="flex-1 p-3.5 overflow-y-auto space-y-2.5 bg-slate-50/50 dark:bg-slate-955/20">
            {messages.map((msg, index) => {
              const isUser = msg.sender === "user";
              return (
                <div
                  key={index}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-[11px] font-medium leading-relaxed ${
                      isUser
                        ? "bg-[#0D53FC] text-white rounded-tr-none"
                        : "bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-100 dark:border-white/5 rounded-tl-none"
                    }`}
                  >
                    {msg.text}
                  </div>
                  <span className="text-[7px] text-slate-400 font-medium mt-0.5 px-0.5">
                    {msg.time}
                  </span>
                </div>
              );
            })}

            {/* Bouncing typing dots */}
            {isTyping && (
              <div className="flex items-center space-x-1 bg-white dark:bg-slate-800 border border-slate-100 dark:border-white/5 rounded-2xl rounded-tl-none px-3 py-2 w-12 select-none">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Form input bar */}
          <form
            onSubmit={handleSendMessage}
            className="p-2 border-t border-slate-100 dark:border-white/5 bg-white dark:bg-slate-900 flex items-center gap-1.5 shrink-0"
          >
            <button
              type="button"
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 bg-transparent border-0 cursor-pointer"
            >
              <Smile className="w-4 h-4" />
            </button>
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/5 rounded-full px-3.5 py-1.5 text-[11px] text-slate-900 dark:text-white focus:outline-none focus:border-[#0D53FC]"
            />
            <button
              type="submit"
              disabled={!inputVal.trim()}
              className="p-1.5 bg-[#0D53FC] hover:bg-[#0a43ca] disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-400 text-white rounded-full border-0 cursor-pointer transition-colors"
            >
              <Send className="w-3 h-3" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
