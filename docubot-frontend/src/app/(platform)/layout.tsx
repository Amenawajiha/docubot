"use client";

import React from "react";
import { Providers, useAuth } from "@/components/providers/Providers";
import FloatingChat from "@/components/layout/FloatingChat";
import Preloader from "@/components/ui/Preloader";

function PlatformContent({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();

  if (loading) {
    return <Preloader />;
  }

  return (
    <>
      {children}
      <FloatingChat />
    </>
  );
}

export default function PlatformLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <PlatformContent>{children}</PlatformContent>
    </Providers>
  );
}