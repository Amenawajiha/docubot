"use client";

import React from "react";
import { Providers } from "@/components/providers/Providers";
import FloatingChat from "@/components/layout/FloatingChat";

export default function PlatformLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      {children}
      <FloatingChat />
    </Providers>
  );
}
