"use client";

import React from "react";
import Image from "next/image";
import { useAuth } from "@/components/providers/Providers";

import Preloader from "@/components/ui/Preloader";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { loading } = useAuth();

  if (loading) {
    return <Preloader />;
  }

  return <>{children}</>;
}
