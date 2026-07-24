"use client";

import React from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen bg-slate-50 dark:bg-[#030712] text-slate-800 dark:text-slate-100 flex flex-col lg:flex-row relative overflow-hidden font-sans transition-colors duration-300">
      {/* Background blurs */}
      <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-blue-600/5 dark:bg-blue-600/10 blur-[120px] pointer-events-none z-0" />

      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden z-10 relative bg-white dark:bg-[#030712] transition-colors duration-300">
        <Header />

        {/* Viewport Content */}
        <div className="flex-1 p-4 sm:p-6 lg:p-6 xl:p-8 overflow-y-auto max-w-[1440px] w-full mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
