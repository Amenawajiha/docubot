"use client";

import React, { useState } from "react";
import { useWorkspace } from "@/components/providers/Providers";

export default function WorkspaceBillingPage() {
  const {
    selectedPlan,
    setSelectedPlan,
    cardName,
    setCardName,
    cardNumber,
    setCardNumber,
    cardExpiry,
    setCardExpiry,
    cardCvv,
    setCardCvv
  } = useWorkspace();

  // Track active plan separately from checkout selected plan to allow plan upgrading
  const [activePlan, setActivePlan] = useState<"starter" | "pro" | "enterprise">("starter");
  const [isUpgrading, setIsUpgrading] = useState(false);

  const handleUpdatePayment = (e: React.FormEvent) => {
    e.preventDefault();
    alert("Payment method updated successfully!");
  };

  const handlePlanUpgrade = () => {
    setIsUpgrading(true);
    setTimeout(() => {
      setIsUpgrading(false);
      setActivePlan(selectedPlan);
      alert(`Success! Workspace plan upgraded to ${selectedPlan === "pro" ? "Professional" : "Starter"} Tier.`);
    }, 1500);
  };

  return (
    <div className="space-y-6 animate-fadeIn text-left max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-[#0a1a2f] dark:text-white tracking-tight">Billing & Subscription</h2>
        <p className="text-xs text-slate-500 mt-1">Manage your plan and payment details.</p>
      </div>

      {/* Top Card: Current Plan Summary */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 flex justify-between items-center shadow-sm relative overflow-hidden">
        <div className="space-y-1 text-left">
          <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">
            CURRENT PLAN
          </p>
          <h3 className="text-base font-extrabold text-[#0a1a2f] dark:text-white">
            {activePlan === "pro" ? "Professional Tier" : "Starter Tier"}
          </h3>
          <p className="text-xs text-slate-500 font-medium">
            {activePlan === "pro" ? "$49/mo" : "$19/mo"} · Renews Aug 2, 2026
          </p>
        </div>

        <div className="text-xs font-bold text-emerald-500 dark:text-emerald-450 shrink-0">
          Active
        </div>
      </div>

      {/* Bottom Grid layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
        {/* Left Column: Select Subscription Plan */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 space-y-5 shadow-sm">
          <h4 className="text-sm font-extrabold text-[#0a1a2f] dark:text-white tracking-tight">
            Select Subscription Plan
          </h4>

          <div className="space-y-4">
            {/* Starter Tier row */}
            <div
              onClick={() => setSelectedPlan("starter")}
              className={`p-5 rounded-2xl border cursor-pointer transition-all flex justify-between items-center ${
                selectedPlan === "starter"
                  ? "border-[#0d53fc] bg-[#0d53fc]/5 dark:bg-[#0d53fc]/10 shadow-sm"
                  : "border-slate-200 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10 bg-white dark:bg-slate-950"
              }`}
            >
              <div className="space-y-1 pr-4">
                <p className="text-xs font-bold text-[#0a1a2f] dark:text-white flex items-center gap-1.5">
                  Starter Tier
                  {activePlan === "starter" && (
                    <span className="text-[8px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-450 px-1.5 py-0.5 rounded-full font-bold">Active</span>
                  )}
                </p>
                <p className="text-[10px] text-slate-500 font-medium">Up to 1,500 messages, 3 PDF attachments.</p>
              </div>
              <div className="text-xs font-extrabold text-[#0a1a2f] dark:text-white shrink-0">
                $19 /mo
              </div>
            </div>

            {/* Professional Tier row */}
            <div
              onClick={() => setSelectedPlan("pro")}
              className={`p-5 rounded-2xl border cursor-pointer transition-all flex justify-between items-center ${
                selectedPlan === "pro"
                  ? "border-[#0d53fc] bg-[#0d53fc]/5 dark:bg-[#0d53fc]/10 shadow-sm"
                  : "border-slate-200 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10 bg-white dark:bg-slate-955"
              }`}
            >
              <div className="space-y-1 pr-4">
                <p className="text-xs font-bold text-[#0a1a2f] dark:text-white flex items-center gap-1.5">
                  Professional Tier
                  {activePlan === "pro" && (
                    <span className="text-[8px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-450 px-1.5 py-0.5 rounded-full font-bold">Active</span>
                  )}
                </p>
                <p className="text-[10px] text-slate-500 font-medium">Up to 15,000 messages, 15 PDF docs.</p>
              </div>
              <div className="text-xs font-extrabold text-[#0a1a2f] dark:text-white shrink-0">
                $49 /mo
              </div>
            </div>

            {/* Upgrade Plan Action Button */}
            {selectedPlan !== activePlan ? (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={handlePlanUpgrade}
                  disabled={isUpgrading}
                  className="w-full bg-[#0D53FC] hover:bg-[#0a43ca] disabled:bg-slate-300 text-white py-3 rounded-xl text-xs font-bold transition-all shadow-sm border-0 cursor-pointer text-center"
                >
                  {isUpgrading
                    ? "Processing Upgrade..."
                    : `Upgrade to ${selectedPlan === "pro" ? "Professional" : "Starter"} Tier`}
                </button>
              </div>
            ) : (
              <div className="pt-2 text-center text-[10px] font-bold text-slate-400">
                ✓ Current Active Plan
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Payment Details form */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 space-y-5 shadow-sm">
          <h4 className="text-sm font-extrabold text-[#0a1a2f] dark:text-white tracking-tight">
            Payment Details
          </h4>

          <form onSubmit={handleUpdatePayment} className="space-y-4">
            <div className="space-y-1.5 font-medium text-left">
              <label className="text-[10px] font-bold text-slate-750 dark:text-slate-400 uppercase tracking-wider">Cardholder Name</label>
              <input
                type="text"
                required
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                placeholder="Jane Doe"
                className="w-full bg-slate-55 dark:bg-slate-955 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none"
              />
            </div>

            <div className="space-y-1.5 font-medium text-left">
              <label className="text-[10px] font-bold text-slate-755 dark:text-slate-400 uppercase tracking-wider">Card Number</label>
              <input
                type="text"
                required
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value)}
                placeholder="4242 4242 4242 4242"
                className="w-full bg-slate-55 dark:bg-slate-950 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 text-left">
              <div className="space-y-1.5 font-medium">
                <label className="text-[10px] font-bold text-slate-755 dark:text-slate-400 uppercase tracking-wider">Expiry</label>
                <input
                  type="text"
                  required
                  value={cardExpiry}
                  onChange={(e) => setCardExpiry(e.target.value)}
                  placeholder="12/28"
                  className="w-full bg-slate-55 dark:bg-slate-905 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none font-mono"
                />
              </div>

              <div className="space-y-1.5 font-medium">
                <label className="text-[10px] font-bold text-slate-755 dark:text-slate-400 uppercase tracking-wider">CVV</label>
                <input
                  type="password"
                  required
                  value={cardCvv}
                  onChange={(e) => setCardCvv(e.target.value)}
                  placeholder="•••"
                  maxLength={3}
                  className="w-full bg-slate-55 dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none font-mono text-center"
                />
              </div>
            </div>

            {/* Form Footer Action buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-100 dark:border-white/5 mt-4">
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  alert("Opening billing invoice center...");
                }}
                className="text-[#0d53fc] hover:underline text-xs font-bold transition-all shrink-0 cursor-pointer text-center sm:text-left"
              >
                View invoice history →
              </a>

              <button
                type="submit"
                className="w-full sm:w-auto bg-[#0d53fc] hover:bg-[#0a43ca] text-white px-5 py-2.5 rounded-xl text-xs font-bold border-0 cursor-pointer transition-colors shadow-sm shrink-0"
              >
                Update Payment Method
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
