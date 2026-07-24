 "use client";

import React, { useState, useRef, useEffect } from "react";
import { Sparkles, Send, User, Bot, Terminal, HelpCircle, Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

type PersonaId = "support" | "tech" | "creative";

interface Persona {
  id: PersonaId;
  name: string;
  role: string;
  welcome: string;
  avatarColor: string;
  quickPrompts: { label: string; prompt: string; response: string }[];
  fallbackResponses: string[];
}

function getRandomFallback(responses: string[]): string {
  const randomIdx = Math.floor(Math.random() * responses.length);
  return responses[randomIdx];
}

export default function CustomChat() {
  const personas: Record<PersonaId, Persona> = {
    support: {
      id: "support",
      name: "Support Specialist",
      role: "Account & Product Help",
      welcome: "Hi! I'm your OmniAI Support Agent. How can I help you with your account, billing, or platform features today?",
      avatarColor: "from-indigo-500 to-blue-500",
      quickPrompts: [
        {
          label: "How do I upgrade my plan?",
          prompt: "How do I upgrade my plan?",
          response: "Upgrading is simple! Head over to the billing tab in your settings panel, select the Pro or Enterprise tier, and click 'Upgrade'. Changes will be applied to your workspace immediately."
        },
        {
          label: "Can I cancel anytime?",
          prompt: "Can I cancel anytime?",
          response: "Yes, absolutely! You can cancel your subscription from your billing dashboard at any time. You will continue to have access to your paid features until the end of your current billing cycle."
        },
        {
          label: "Is there a free trial?",
          prompt: "Is there a free trial?",
          response: "Yes! Our Starter plan is 100% free for up to 500 messages per month, and we offer a 14-day free trial on our Professional tier. No credit card is required to sign up."
        }
      ],
      fallbackResponses: [
        "That is a great support question! You can configure that directly inside the OmniAI Settings console under the Advanced tab.",
        "I've noted your request. If you need immediate human assistance, please type 'Submit Ticket' and I'll route this to our support desk.",
        "You can find detailed documentation on this in our Help Center or contact our billing desk at billing@omniai.com."
      ]
    },
    tech: {
      id: "tech",
      name: "DevOps Tech Guru",
      role: "Integrations & API Expert",
      welcome: "Hey there! Tech Guru here. Need help with integrations, database schemas, or writing some clean code? Fire away!",
      avatarColor: "from-cyan-500 to-emerald-500",
      quickPrompts: [
        {
          label: "Next.js API route template",
          prompt: "Write a Next.js API route.",
          response: "Here is a clean Next.js API route template using TypeScript and App Router standard:\n\n```typescript\nimport { NextResponse } from 'next/server';\n\nexport async function POST(req: Request) {\n  try {\n    const data = await req.json();\n    // Process your logic here\n    return NextResponse.json({ success: true, data });\n  } catch (error) {\n    return NextResponse.json(\n      { error: 'Invalid payload' },\n      { status: 400 }\n    );\n  }\n}\n```"
        },
        {
          label: "How does RAG work?",
          prompt: "Explain how Retrieval-Augmented Generation (RAG) works.",
          response: "Retrieval-Augmented Generation (RAG) combines custom data retrieval with LLMs. First, you convert your documents (PDFs, docs) into vector embeddings. When a user asks a question, we query a vector database (e.g. Pinecone) to find the most relevant chunks. We then append these chunks to the LLM context, yielding a highly accurate, hallucination-free response."
        },
        {
          label: "How to secure webhooks?",
          prompt: "How do I secure webhooks?",
          response: "To secure webhooks, we sign the payload with a cryptographic SHA-256 HMAC signature. When you receive a webhook, you calculate the HMAC hash using your unique workspace webhook secret and compare it with the signature sent in our custom `X-OmniAI-Signature` HTTP header. This ensures the request is authentic and unmodified."
        }
      ],
      fallbackResponses: [
        "That's an interesting technical implementation. Usually, you would implement this using standard React fetch requests or by importing our custom npm SDK `@omniai/sdk`.",
        "If you want to review full API request and response structures, check our developer docs at developers.omniai.com.",
        "To debug this further, verify your workspace API tokens are loaded correctly into your environment variables as `OMNIAI_API_KEY`."
      ]
    },
    creative: {
      id: "creative",
      name: "Creative Strategist",
      role: "Copywriter & Brainstormer",
      welcome: "Greetings, traveler! I am the Creative Strategist. Need a tagline, blog hook, or a clever analogy? Let's summon some words!",
      avatarColor: "from-purple-500 to-pink-500",
      quickPrompts: [
        {
          label: "Draft a product launch tweet",
          prompt: "Draft a product launch tweet for OmniAI.",
          response: "🚀 Say hello to OmniAI 2.0! We are transforming how businesses communicate. Real-time NLP, deep vector knowledge search, and automated workflows. Built for builders, trusted by enterprise. Converse. Automate. Elevate. \n\nTry the sandbox free! 👇 \n#AI #ProductLaunch #TechTrends"
        },
        {
          label: "Catchy chatbot taglines",
          prompt: "Create a catchy tagline for our chatbot website.",
          response: "Here are a few options depending on your brand's vibe:\n\n1. *'FAQ is dead. Long live conversation.'*\n2. *'Human-grade support, robot-scale speed.'*\n3. *'Turn clicks into conversations and tickets into solutions.'*\n\nWhich style resonates most with your brand?"
        },
        {
          label: "Explain AI to a 5-year old",
          prompt: "Explain AI to a 5-year old.",
          response: "Imagine you have a super-smart toy robot. If you show it a picture of a puppy, it learns what a puppy looks like. Eventually, it can look at any picture and say, 'That is a doggy!' AI is like a giant computer friend that learns from pictures and stories to help us solve puzzles!"
        }
      ],
      fallbackResponses: [
        "What a brilliant spark of inspiration! Let's brainstorm how to expand this concept into a full multichannel marketing campaign.",
        "To make that description stand out, we could add vivid sensory words or use a direct, active verbs format.",
        "I love this angle! Let's write a quick outline or outline the core benefits to see how it sits with the audience."
      ]
    }
  };

  const [activePersonaId, setActivePersonaId] = useState<PersonaId>("support");
  const activePersona = personas[activePersonaId];

  // Chat message state initialized per persona
  const [chats, setChats] = useState<Record<PersonaId, { sender: "user" | "bot"; text: string }[]>>({
    support: [{ sender: "bot", text: personas.support.welcome }],
    tech: [{ sender: "bot", text: personas.tech.welcome }],
    creative: [{ sender: "bot", text: personas.creative.welcome }]
  });

  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chats, isTyping, activePersonaId]);

  const handleSendMessage = (text: string) => {
    if (!text.trim()) return;

    // Append user message
    const currentChats = [...chats[activePersonaId], { sender: "user", text }];
    setChats({
      ...chats,
      [activePersonaId]: currentChats
    });
    setInputValue("");

    // Simulate bot typing
    setIsTyping(true);

    // Determine bot response
    let responseText = "";
    
    // Check if it matches quick prompts exactly
    const matchingPrompt = activePersona.quickPrompts.find(
      (p) => p.prompt.toLowerCase() === text.toLowerCase() || p.label.toLowerCase() === text.toLowerCase()
    );

    if (matchingPrompt) {
      responseText = matchingPrompt.response;
    } else {
      // Pick random fallback response
      responseText = getRandomFallback(activePersona.fallbackResponses);
    }

    setTimeout(() => {
      setIsTyping(false);
      setChats((prev) => ({
        ...prev,
        [activePersonaId]: [...prev[activePersonaId], { sender: "bot", text: responseText }]
      }));
    }, 1500); // 1.5 seconds typing speed simulator
  };

  const currentChatHistory = chats[activePersonaId];

  // Helper to format response text (supporting simple code blocks)
  const renderMessageContent = (text: string) => {
    if (text.includes("```")) {
      const parts = text.split("```");
      return parts.map((part, index) => {
        if (index % 2 === 1) {
          // Inside code block
          const lines = part.split("\n");
          const lang = lines[0] || "javascript";
          const code = lines.slice(1).join("\n");
          return (
            <div key={index} className="my-3 font-mono text-[11px] bg-slate-950 border border-white/10 rounded-xl overflow-hidden shadow-lg w-full max-w-full">
              <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-white/5 text-slate-400 text-[10px]">
                <span className="flex items-center space-x-1.5">
                  <Terminal className="w-3 h-3 text-cyan-400" />
                  <span>{lang}</span>
                </span>
                <span className="text-[10px] text-slate-500 uppercase">Live Template</span>
              </div>
              <pre className="p-3.5 overflow-x-auto text-cyan-200/90 whitespace-pre scrollbar-thin">
                <code>{code}</code>
              </pre>
            </div>
          );
        }
        return <p key={index} className="whitespace-pre-line">{part}</p>;
      });
    }
    return <p className="whitespace-pre-line">{text}</p>;
  };

  return (
    <section id="sandbox" className="py-24 bg-slate-950 relative border-t border-white/5 scroll-mt-12">
      {/* Visual background glows */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[500px] h-[500px] bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header Title */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <Badge variant="secondary" className="py-1 px-3">
            Sandbox Playground
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            Interact with our AI Agent Personas
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Select a specialized AI personality, click on quick test prompts, or type custom queries to test the speed and accuracy of the OmniAI system.
          </p>
        </div>

        {/* Sandbox Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* Left Column: Persona Selector and Quick Actions */}
          <div className="lg:col-span-4 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <h3 className="text-base font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <Sparkles className="w-4.5 h-4.5 text-indigo-400" />
                <span>1. Select Persona</span>
              </h3>

              {/* Persona Cards */}
              <div className="flex flex-col space-y-3">
                {(Object.keys(personas) as PersonaId[]).map((pKey) => {
                  const p = personas[pKey];
                  const isActive = activePersonaId === pKey;
                  return (
                    <button
                      key={pKey}
                      onClick={() => setActivePersonaId(pKey)}
                      className={`w-full text-left p-4 rounded-2xl transition-all duration-300 border flex items-center space-x-4 cursor-pointer ${
                        isActive
                          ? "bg-indigo-500/10 border-indigo-500/40 shadow-[0_0_20px_rgba(99,102,241,0.1)]"
                          : "bg-slate-900/30 border-white/5 hover:border-white/10 hover:bg-slate-900/50"
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${p.avatarColor} flex items-center justify-center text-white font-bold shadow-lg`}>
                        {p.name.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-white leading-tight">{p.name}</h4>
                        <p className="text-[11px] text-slate-400 truncate mt-0.5">{p.role}</p>
                      </div>
                      {isActive && (
                        <div className="w-5 h-5 bg-indigo-500/20 border border-indigo-500/40 rounded-full flex items-center justify-center text-indigo-400">
                          <Check className="w-3 h-3" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quick Prompts List */}
            <div className="space-y-3 pt-4 lg:pt-0">
              <h3 className="text-base font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <HelpCircle className="w-4.5 h-4.5 text-cyan-400" />
                <span>2. Suggested Prompts</span>
              </h3>
              <div className="flex flex-wrap lg:flex-col gap-2">
                {activePersona.quickPrompts.map((qp, idx) => (
                  <button
                    key={idx}
                    disabled={isTyping}
                    onClick={() => handleSendMessage(qp.prompt)}
                    className="text-left text-[11px] sm:text-xs text-slate-300 hover:text-white px-3 py-2 bg-slate-900/60 hover:bg-indigo-500/10 border border-white/5 hover:border-indigo-500/30 rounded-xl transition-all duration-300 flex-1 min-w-[150px] sm:min-w-[200px] lg:w-full truncate disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                  >
                    💡 {qp.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Terminal Chat Interface */}
          <div className="lg:col-span-8">
            <Card className="h-[550px] border border-white/10 flex flex-col p-0 overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.6)] bg-slate-950/80 backdrop-blur-md">
              {/* Chat Window Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-slate-900/30">
                <div className="flex items-center space-x-3.5">
                  <div className={`w-3 h-3 rounded-full bg-gradient-to-tr ${activePersona.avatarColor} animate-pulse-glow`} />
                  <div>
                    <span className="text-sm font-semibold text-white tracking-tight">
                      {activePersona.name}
                    </span>
                    <span className="text-[10px] text-slate-400 ml-2 border border-slate-700 rounded-md px-1.5 py-0.5 bg-slate-900/50">
                      Sandbox active
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-1.5 text-xs text-slate-400">
                  <Terminal className="w-3.5 h-3.5 text-slate-500" />
                  <span className="font-mono text-[10px]">Session: omni-sandbox-t1</span>
                </div>
              </div>

              {/* Chat Messages Log */}
              <div className="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-thin">
                {currentChatHistory.map((chat, idx) => (
                  <div
                    key={idx}
                    className={`flex items-start gap-3.5 ${
                      chat.sender === "user" ? "flex-row-reverse" : ""
                    }`}
                  >
                    {/* Icon Avatar */}
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white font-bold text-xs ${
                      chat.sender === "user"
                        ? "bg-indigo-600 shadow-md"
                        : `bg-gradient-to-br ${activePersona.avatarColor} shadow-md`
                    }`}>
                      {chat.sender === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    {/* Chat Bubble content */}
                    <div className={`p-4 rounded-2xl text-xs sm:text-sm max-w-[82%] shadow-md border ${
                      chat.sender === "user"
                        ? "bg-indigo-600 border-indigo-500 text-white rounded-tr-none"
                        : "bg-slate-900/70 border-white/5 text-slate-200 rounded-tl-none"
                    }`}>
                      {chat.sender === "user" ? (
                        <p className="whitespace-pre-line">{chat.text}</p>
                      ) : (
                        renderMessageContent(chat.text)
                      )}
                    </div>
                  </div>
                ))}

                {/* Simulated AI typing delay bubbles */}
                {isTyping && (
                  <div className="flex items-start gap-3.5">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-white font-bold text-xs bg-gradient-to-br ${activePersona.avatarColor}`}>
                      <Bot className="w-4 h-4" />
                    </div>
                    <div className="p-3 bg-slate-900/50 border border-white/5 rounded-2xl rounded-tl-none flex items-center space-x-1.5">
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                      <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Bar */}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(inputValue);
                }}
                className="p-4 border-t border-white/5 bg-slate-900/20 flex gap-3 items-center"
              >
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={isTyping}
                  placeholder={`Send a query to ${activePersona.name}...`}
                  className="flex-1 bg-slate-900 border border-white/5 rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-300 disabled:opacity-50"
                />
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isTyping || !inputValue.trim()}
                  className="py-3 px-4 rounded-xl flex items-center justify-center"
                >
                  <Send className="w-4.5 h-4.5" />
                </Button>
              </form>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
