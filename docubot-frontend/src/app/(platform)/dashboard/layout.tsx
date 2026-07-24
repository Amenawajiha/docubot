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
      <div className="min-h-screen bg-white dark:bg-[#030712] flex flex-col items-center justify-center text-slate-800 dark:text-white">
        <div className="relative w-80 h-80 mb-6 flex items-center justify-center">
          <div className="absolute w-64 h-64 bg-[#0052ff]/10 dark:bg-blue-600/10 rounded-full blur-2xl animate-pulse" />
          <div className="absolute inset-0 rounded-full border-2 border-t-[#0052ff] border-r-transparent border-b-[#0052ff]/40 border-l-transparent animate-spin" style={{ animationDuration: "3s" }} />
          <Image
            src="/images/chat bot icon_2.gif"
            alt="Loading..."
            width={320}
            height={320}
            unoptimized
            className="w-full h-full object-contain relative z-10 p-8"
          />
        </div>
        <p className="text-slate-400 dark:text-slate-500 font-bold text-xs uppercase tracking-widest animate-pulse">
          Loading assistant engine...
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
