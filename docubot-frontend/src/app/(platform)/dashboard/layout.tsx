"use client";

import React from "react";
import Image from "next/image";
import { useAuth } from "@/components/providers/Providers";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030712] flex flex-col items-center justify-center text-white">
        <div className="relative w-80 h-80 mb-6 flex items-center justify-center">
          <video autoPlay loop muted playsInline className="w-full h-full object-contain relative z-10 p-8 mix-blend-screen">
            <source src="/images/loading.webm" type="video/webm"/>
          </video>
        </div>
        <p className="text-slate-400 font-bold text-xs uppercase tracking-widest animate-pulse">
          Loading SYNQDOC AI...
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
