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
