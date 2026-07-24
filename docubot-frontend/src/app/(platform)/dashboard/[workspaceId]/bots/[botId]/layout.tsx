"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { useWorkspace } from "@/components/providers/Providers";
import { Settings, Brain, Globe, BarChart3, Terminal } from "lucide-react";

export default function BotDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { workspaceId, currentChatbot } = useWorkspace();

  const tabs = [
    { id: "settings", label: "AI Studio (Settings)", icon: Settings, path: `/dashboard/${workspaceId}/bots/${currentChatbot?.id}/settings` },
    { id: "playground", label: "Testing Playground", icon: Terminal, path: `/dashboard/${workspaceId}/bots/${currentChatbot?.id}/playground` },
    { id: "knowledge", label: "Knowledge Base", icon: Brain, path: `/dashboard/${workspaceId}/bots/${currentChatbot?.id}/knowledge` },
    { id: "deployment", label: "Deployment", icon: Globe, path: `/dashboard/${workspaceId}/bots/${currentChatbot?.id}/deployment` },
    { id: "analytics", label: "Analytics & Reporting", icon: BarChart3, path: `/dashboard/${workspaceId}/bots/${currentChatbot?.id}/analytics` }
  ];

  return (
    <div className="space-y-6">
      {/* Dynamic horizontal subpage navigation tabs */}
      <div className="flex border-b border-slate-200 dark:border-white/5 pb-1 overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = pathname === tab.path || (tab.id === "settings" && pathname === `/dashboard/${workspaceId}/bots/${currentChatbot?.id}`);
          return (
            <button
              key={tab.id}
              onClick={() => router.push(tab.path)}
              className={`flex items-center gap-2 pb-3.5 px-4 text-xs font-bold transition-all relative border-0 bg-transparent cursor-pointer whitespace-nowrap ${
                isActive ? "text-[#0D53FC] dark:text-blue-400" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" />
              <span>{tab.label}</span>
              {isActive && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#0D53FC] dark:bg-blue-400" />}
            </button>
          );
        })}
      </div>

      {/* Children views */}
      <div className="pt-2">{children}</div>
    </div>
  );
}
