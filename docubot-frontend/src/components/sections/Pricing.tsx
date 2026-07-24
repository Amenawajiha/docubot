"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Pricing() {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const router = useRouter();

  useEffect(() => {
    // Check if user is logged in
    setIsLoggedIn(localStorage.getItem("isLoggedIn") === "true");
    const checkAuth = () => {
      setIsLoggedIn(localStorage.getItem("isLoggedIn") === "true");
    };
    window.addEventListener("storage", checkAuth);
    return () => {
      window.removeEventListener("storage", checkAuth);
    };
  }, []);

  const handleAction = (planName: string) => {
    if (planName === "BUSINESS") {
      window.location.href = "mailto:sales@docubot.ai?subject=Inquiry about Business Plan";
      return;
    }

    if (isLoggedIn) {
      router.push("/dashboard");
    } else {
      const event = new CustomEvent("open-auth-modal", {
        detail: { mode: "signin" }
      });
      window.dispatchEvent(event);
    }
  };

  const plans = [
    {
      name: "FREE",
      price: 0,
      description: "Explore document AI free — perfect for testing your assistant.",
      features: [
        { text: "1 active chatbot", included: true },
        { text: "Playground & shareable link", included: true },
        { text: "GPT-4o Mini (shared)", included: true },
        { text: "Basic customization", included: true },
        { text: "Website widget embed", included: false },
        { text: "Public deployment", included: false },
      ],
      ctaText: "Get started free",
      popular: false,
    },
    {
      name: "PRO",
      price: billingPeriod === "monthly" ? 49 : 37,
      description: "Everything to go live — Bot Studio, analytics, API & deployments.",
      features: [
        { text: "Public deployment", included: true },
        { text: "10 active chatbots", included: true },
        { text: "GPT-4o + Claude", included: true },
        { text: "Analytics + REST API", included: true },
        { text: "Slack + WhatsApp", included: true },
        { text: "Remove branding", included: true },
      ],
      ctaText: "Start free trial",
      popular: true,
    },
    {
      name: "BUSINESS",
      price: billingPeriod === "monthly" ? 99 : 74,
      description: "High-volume teams with custom domains and SLA-backed uptime.",
      features: [
        { text: "Unlimited chatbots", included: true },
        { text: "White-label + custom domain", included: true },
        { text: "Smart escalation engine", included: true },
        { text: "Google Drive & Notion sync", included: true },
        { text: "PII masking & retention", included: true },
        { text: "Priority support", included: true },
      ],
      ctaText: "Contact sales",
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="py-24 bg-white dark:bg-[#030712] relative border-t border-slate-200 dark:border-white/5 scroll-mt-16 transition-colors duration-300 overflow-hidden">
      {/* Background glow effects to match Coinbase premium design */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-blue-600/5 dark:bg-blue-600/10 rounded-full blur-[140px] pointer-events-none z-0" />
      
      <div className="max-w-7xl mx-auto px-6 relative z-10">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-extrabold uppercase tracking-[0.25em] text-[#0052ff] dark:text-[#3b82f6]">
            Transparent Pricing
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white mt-3">
            Plans to match your ambitions
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-4 text-sm sm:text-base max-w-xl mx-auto font-medium">
            Start free and scale as you grow — deploy when you're ready to go live.
          </p>
        </div>

        {/* Billing Toggle Switch */}
        <div className="flex justify-center mb-16">
          <div className="inline-flex items-center p-1 bg-slate-100 dark:bg-slate-900/60 border border-slate-200 dark:border-white/5 rounded-full transition-all duration-300">
            <button
              onClick={() => setBillingPeriod("monthly")}
              className={`px-6 py-2 rounded-full text-xs font-bold transition-all duration-300 cursor-pointer ${
                billingPeriod === "monthly"
                  ? "bg-[#0052ff] text-white shadow-[0_4px_12px_rgba(13,83,252,0.25)]"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod("yearly")}
              className={`px-6 py-2 rounded-full text-xs font-bold transition-all duration-300 flex items-center space-x-1.5 cursor-pointer ${
                billingPeriod === "yearly"
                  ? "bg-[#0052ff] text-white shadow-[0_4px_12px_rgba(13,83,252,0.25)]"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <span>Yearly</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold transition-colors duration-300 ${
                billingPeriod === "yearly"
                  ? "bg-white/20 text-white"
                  : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
              }`}>
                Save 25%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch max-w-5xl mx-auto px-2 md:px-0">
          {plans.map((plan, idx) => (
            <div
              key={idx}
              className={`flex flex-col h-full rounded-3xl transition-all duration-350 relative ${
                plan.popular
                  ? "bg-[#0052ff] text-white p-8 md:-translate-y-2 md:scale-[1.03] z-10 shadow-[0_20px_50px_rgba(13,83,252,0.35)] border border-[#2b6eff]"
                  : "bg-white dark:bg-[#070b15] border border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/80 p-8 shadow-sm dark:shadow-xl dark:shadow-black/20"
              }`}
            >
              {/* Popular Ribbon Tag */}
              {plan.popular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span className="bg-white text-[#0052ff] py-1 px-3.5 uppercase tracking-wider text-[10px] font-extrabold rounded-full shadow-md">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Plan Header */}
              <div className="mb-6">
                <h3 className={`text-sm font-extrabold uppercase tracking-wider ${
                  plan.popular ? "text-blue-100" : "text-[#0052ff] dark:text-[#3b82f6]"
                }`}>
                  {plan.name}
                </h3>
                
                {/* Price */}
                <div className="flex items-baseline mt-4 mb-3">
                  <span className="text-5xl font-extrabold tracking-tight">
                    ${plan.price}
                  </span>
                  <span className={`text-xs font-semibold ml-2 ${
                    plan.popular ? "text-blue-100/70" : "text-slate-400"
                  }`}>
                    / month
                  </span>
                </div>
                
                <p className={`text-xs leading-relaxed font-medium min-h-[40px] ${
                  plan.popular ? "text-blue-100/80" : "text-slate-500 dark:text-slate-400"
                }`}>
                  {plan.description}
                </p>
              </div>

              {/* Divider */}
              <div className={`h-[1px] w-full mb-6 ${
                plan.popular ? "bg-white/10" : "bg-slate-200/60 dark:bg-white/5"
              }`} />

              {/* Features List */}
              <ul className="space-y-4 flex-1 mb-8">
                {plan.features.map((feature, fIdx) => (
                  <li key={fIdx} className="flex items-start text-xs font-semibold">
                    {feature.included ? (
                      /* Included Checkmark */
                      plan.popular ? (
                        <div className="w-4 h-4 rounded-full bg-white/20 text-white flex items-center justify-center shrink-0 mt-0.5 mr-3">
                          <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      ) : (
                        <div className="w-4 h-4 rounded-full bg-emerald-500/10 text-emerald-500 dark:text-emerald-450 flex items-center justify-center shrink-0 mt-0.5 mr-3 border border-emerald-500/10">
                          <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        </div>
                      )
                    ) : (
                      /* Excluded X */
                      <div className="w-4 h-4 rounded-full bg-slate-100 dark:bg-slate-900/80 text-slate-400 dark:text-slate-600 flex items-center justify-center shrink-0 mt-0.5 mr-3 border border-slate-200/50 dark:border-white/5">
                        <svg className="w-2 h-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </div>
                    )}
                    <span className={`${
                      !feature.included 
                        ? (plan.popular ? "text-white/40" : "text-slate-400/70 dark:text-slate-500/70 line-through")
                        : (plan.popular ? "text-white" : "text-slate-700 dark:text-slate-300")
                    }`}>
                      {feature.text}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA Button */}
              <button
                onClick={() => handleAction(plan.name)}
                className={`w-full py-3.5 px-6 rounded-xl text-xs font-bold transition-all duration-300 cursor-pointer text-center block ${
                  plan.popular
                    ? "bg-white hover:bg-slate-50 text-[#0052ff] shadow-lg hover:shadow-xl hover:scale-[1.01]"
                    : "bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-800 dark:text-white"
                }`}
              >
                {plan.ctaText}
              </button>
            </div>
          ))}
        </div>

        {/* Footnote */}
        <div className="text-center mt-12">
          <p className="text-xs text-slate-400 dark:text-slate-500 font-semibold tracking-wide">
            No credit card required on Free · Cancel anytime on paid plans
          </p>
        </div>

      </div>
    </section>
  );
}
