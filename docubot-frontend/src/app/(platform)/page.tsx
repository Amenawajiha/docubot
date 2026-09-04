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

import Preloader from "@/components/ui/Preloader";

export default function Home() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <Preloader />;
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