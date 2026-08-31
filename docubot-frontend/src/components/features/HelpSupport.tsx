"use client";

import React from "react";
import {
  Search, BookOpen, MessageCircle, Bell,
  ExternalLink, FileText, Zap, ShieldCheck,
  Users, HelpCircle, ArrowUpRight,
} from "lucide-react";

export default function HelpSupport() {
  const quickCards = [
    { title: "Documentation", desc: "Guides, tutorials, and API reference", icon: BookOpen, link: "#" },
    { title: "Live Chat", desc: "Talk to our support team now", icon: MessageCircle, link: "#" },
    { title: "Changelog", desc: "Latest updates and new features", icon: Bell, link: "#" },
  ];

  const articles = [
    { title: "Getting Started with SYNQDOC", category: "Onboarding", icon: Zap },
    { title: "How to Train Your Chatbot with Documents", category: "Knowledge", icon: FileText },
    { title: "Understanding Role-Based Access", category: "Security", icon: ShieldCheck },
    { title: "Deploying to Your Website", category: "Deployment", icon: ExternalLink },
    { title: "Inviting Team Members", category: "Collaboration", icon: Users },
    { title: "Billing & Subscription FAQ", category: "Account", icon: HelpCircle },
  ];

  return (
    <div className="space-y-5 max-w-5xl">
      {/* ── Dark Header with Search ── */}
      <div className="bg-[#0a0b0d] rounded-2xl p-8 text-center">
        <h1 className="text-xl font-semibold text-white mb-2">How can we help you?</h1>
        <p className="text-sm text-[#7c828a] mb-5">Search our guides, docs, and FAQs</p>
        <div className="max-w-md mx-auto flex items-center gap-2 h-11 px-4 bg-white/10 border border-white/10 rounded-full focus-within:ring-2 focus-within:ring-[#0052ff]">
          <Search size={14} className="text-[#7c828a] shrink-0" />
          <input className="flex-1 bg-transparent text-sm text-white placeholder-[#7c828a] outline-none" placeholder="Search help articles…" />
        </div>
      </div>

      {/* ── Quick Access Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {quickCards.map(card => (
          <a key={card.title} href={card.link}
            className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-5 hover:border-[#0052ff]/40 transition-all group">
            <div className="w-9 h-9 rounded-xl bg-[#f0f5ff] flex items-center justify-center mb-3 group-hover:bg-[#dce8ff] transition-colors">
              <card.icon size={16} className="text-[#0052ff]" />
            </div>
            <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white mb-0.5">{card.title}</p>
            <p className="text-xs text-[#7c828a]">{card.desc}</p>
          </a>
        ))}
      </div>

      {/* ── Popular Articles ── */}
      <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 overflow-hidden">
        <div className="px-5 py-4 border-b border-[#dee1e6] dark:border-white/5">
          <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Popular Articles</p>
          <p className="text-xs text-[#7c828a] mt-0.5">Most-read guides from our knowledge base</p>
        </div>
        {articles.map((article, i) => (
          <a key={i} href="#"
            className={`flex items-center gap-4 px-5 py-4 hover:bg-[#f7f7f7] dark:hover:bg-white/3 transition-colors ${i < articles.length - 1 ? "border-b border-[#dee1e6] dark:border-white/5" : ""}`}>
            <div className="w-8 h-8 rounded-xl bg-[#f0f5ff] flex items-center justify-center shrink-0">
              <article.icon size={14} className="text-[#0052ff]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white">{article.title}</p>
              <p className="text-xs text-[#7c828a] mt-0.5">{article.category}</p>
            </div>
            <ArrowUpRight size={13} className="text-[#a8acb3] shrink-0" />
          </a>
        ))}
      </div>

      {/* ── Still need help ── */}
      <div className="bg-[#f0f5ff] rounded-2xl border border-[#0052ff]/20 p-5 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-[#0052ff] flex items-center justify-center shrink-0">
          <MessageCircle size={18} className="text-white" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-[#0a0b0d]">Still need help?</p>
          <p className="text-xs text-[#5b616e]">Our support team is available 24/7.</p>
        </div>
        <button className="h-8 px-4 rounded-full bg-[#0052ff] text-white text-xs font-semibold hover:bg-[#003ecc] transition-colors">Contact Support</button>
      </div>
    </div>
  );
}
