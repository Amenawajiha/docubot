"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import Header from "@/components/sections/Header";
import Hero from "@/components/sections/Hero";
import Steps from "@/components/sections/Steps";
import Features from "@/components/sections/Features";
import Pricing from "@/components/sections/Pricing";
import WhyChooseUs from "@/components/sections/WhyChooseUs";
import Testimonials from "@/components/sections/Testimonials";
import DemoVideo from "@/components/sections/DemoVideo";
import FAQ from "@/components/sections/FAQ";
import CTA from "@/components/sections/CTA";
import Footer from "@/components/sections/Footer";

export default function Home() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

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
          Loading DocuBot AI...
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground transition-colors duration-300">
      <Header />
      <main className="flex-1">
        <Hero />
        <Steps />
        <Features />
        <Pricing />
        <WhyChooseUs />
        <Testimonials />
        <DemoVideo />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
