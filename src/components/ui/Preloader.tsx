"use client";

import React from "react";
import Image from "next/image";

export default function Preloader() {
  return (
    <div className="min-h-screen w-full bg-white flex flex-col items-center justify-center text-slate-900 transition-colors duration-300 relative overflow-hidden">
      {/* Background ambient radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[320px] h-[320px] bg-blue-500/5 rounded-full blur-[80px] pointer-events-none z-0" />

      {/* Main Preloader graphic wrapper - Proportional Compact Size */}
      <div className="relative w-48 h-48 sm:w-56 sm:h-56 md:w-64 md:h-64 mb-6 flex items-center justify-center z-10">
        
        {/* Outer Orbiting Ring with Nodes */}
        <div className="absolute inset-0 rounded-full border border-blue-500/30 animate-[spin_12s_linear_infinite]">
          {/* 8 Orbital Nodes along the ring - Sharp, Clear & Crisp */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute top-[14.6%] right-[14.6%] translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute top-1/2 right-0 translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute bottom-[14.6%] right-[14.6%] translate-x-1/2 translate-y-1/2 w-3 h-3 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-3.5 h-3.5 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute bottom-[14.6%] left-[14.6%] -translate-x-1/2 translate-y-1/2 w-3 h-3 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute top-1/2 left-0 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
          <div className="absolute top-[14.6%] left-[14.6%] -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-[#0052ff] rounded-full border-2 border-white shadow-sm" />
        </div>

        {/* Counter-rotating Inner Decorative Ring */}
        <div className="absolute inset-[15%] rounded-full border border-dashed border-blue-400/25 animate-[spin_18s_linear_infinite_reverse]" />

        {/* Subtle Pulse Ring */}
        <div className="absolute inset-[25%] rounded-full bg-blue-500/5 animate-ping opacity-75" />

        {/* Center Logo Icon */}
        <div className="relative z-20 w-24 h-24 sm:w-28 sm:h-28 md:w-32 md:h-32 flex items-center justify-center drop-shadow-[0_8px_20px_rgba(13,83,252,0.18)]">
          <Image
            src="/icon.svg"
            alt="SYNQDOC AI"
            width={128}
            height={128}
            priority
            className="w-full h-full object-contain"
          />
        </div>
      </div>

      {/* Loading Text & Status */}
      <div className="flex items-center gap-2.5 z-10">
        <div className="relative flex items-center justify-center w-3.5 h-3.5">
          <span className="absolute w-3.5 h-3.5 rounded-full bg-[#0052ff] animate-ping opacity-30" />
          <span className="relative w-2.5 h-2.5 rounded-full bg-[#0052ff] border border-white shadow-sm" />
        </div>
        <p className="text-slate-600 font-semibold text-xs sm:text-sm uppercase tracking-[0.2em] animate-pulse">
          Loading SYNQDOC AI...
        </p>
      </div>
    </div>
  );
}
