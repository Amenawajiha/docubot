"use client";

import React, { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const faqs: FAQItem[] = [
    {
      question: "How does DocuBot AI train on my documents?",
      answer: "DocuBot AI parses your uploaded PDF, TXT, or CSV files using advanced retrieval-augmented generation (RAG). It creates a semantic database of your content, allowing the chatbot to answer user queries accurately using only the facts in your documents, avoiding hallucinations.",
    },
    {
      question: "Can I customize the design and behavior of my chatbot?",
      answer: "Yes! In the Bot Studio dashboard, you can white-label the widget by altering colors, uploading your logo, modifying the initial greeting message, and choosing between professional, friendly, or playful communication tones.",
    },
    {
      question: "How do I embed the chatbot widget on my website?",
      answer: "We provide a single-line JavaScript `<script>` tag in the dashboard under the Deploy tab. Simply copy it and paste it into the footer or body of your HTML. It is compatible with React, WordPress, Shopify, Webflow, and any standard website platform.",
    },
    {
      question: "Does DocuBot AI support multiple languages?",
      answer: "Absolutely. Powered by GPT-4o and Claude models, our chatbots natively understand and respond in over 95 languages. The bot automatically detects the user's input language and replies in the same language.",
    },
    {
      question: "Is my data secure and private?",
      answer: "Yes, security is our top priority. All uploaded files are encrypted at rest and in transit. Your proprietary data is kept private and is never used to train public LLM foundation models.",
    },
    {
      question: "Can I cancel or change my plan anytime?",
      answer: "Yes, you can upgrade, downgrade, or cancel your subscription at any time directly from the settings page. If you cancel, your paid benefits will continue until the end of your current billing period.",
    },
  ];

  return (
    <section id="faq" className="py-24 bg-white dark:bg-[#030712] relative border-t border-slate-200 dark:border-white/5 scroll-mt-16 transition-colors duration-300 overflow-hidden">
      
      {/* Background glow elements */}
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[300px] bg-blue-600/5 dark:bg-blue-600/10 rounded-full blur-[120px] pointer-events-none z-0" />

      <div className="max-w-4xl mx-auto px-6 relative z-10">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-extrabold uppercase tracking-[0.25em] text-[#0052ff] dark:text-[#3b82f6]">
            Questions & Answers
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white mt-3">
            Frequently Asked Questions
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-4 text-sm sm:text-base max-w-xl mx-auto font-medium">
            Have questions about DocuBot AI? Here are the most common questions and answers.
          </p>
        </div>

        {/* FAQs Accordion Container */}
        <div className="space-y-4 max-w-3xl mx-auto">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className={`border rounded-2xl transition-all duration-300 overflow-hidden bg-white dark:bg-[#070b15] ${
                  isOpen
                    ? "border-[#0052ff]/50 dark:border-[#0052ff]/50 shadow-[0_4px_20px_rgba(13,83,252,0.06)]"
                    : "border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/80"
                }`}
              >
                {/* Accordion Trigger Header Button */}
                <button
                  onClick={() => toggleFAQ(idx)}
                  className="w-full flex items-center justify-between p-5 text-left transition-colors cursor-pointer group"
                >
                  <div className="flex items-center space-x-3.5 pr-4">
                    <HelpCircle className={`w-4 h-4 shrink-0 transition-colors duration-300 ${
                      isOpen ? "text-[#0052ff]" : "text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-300"
                    }`} />
                    <span className="text-sm font-bold text-slate-800 dark:text-slate-200 group-hover:text-[#0052ff] dark:group-hover:text-[#3b82f6] transition-colors duration-300">
                      {faq.question}
                    </span>
                  </div>
                  <div className={`w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-900/80 flex items-center justify-center shrink-0 border border-slate-200/50 dark:border-white/5 transition-all duration-300 ${
                    isOpen ? "rotate-180 bg-[#0052ff]/10 dark:bg-[#0052ff]/15 text-[#0052ff]" : "text-slate-500"
                  }`}>
                    <ChevronDown className="w-3.5 h-3.5" />
                  </div>
                </button>

                {/* Accordion Content Panel with slide/fade animation */}
                <div
                  className={`transition-all duration-300 ease-in-out ${
                    isOpen ? "max-h-[500px] border-t border-slate-200/50 dark:border-white/5" : "max-h-0 pointer-events-none"
                  }`}
                >
                  <div className="p-5 text-xs sm:text-sm font-semibold leading-relaxed text-slate-500 dark:text-slate-400 bg-slate-50/50 dark:bg-[#050912]/20">
                    {faq.answer}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
