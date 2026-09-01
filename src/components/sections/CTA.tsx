"use client";

import React from "react";
import Image from "next/image";
import { Button } from "@/components/ui/Button";

export default function CTA() {
  return (
    <section id="cta" className="py-20 md:py-28 bg-transparent overflow-hidden relative transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 relative">

        {/* Main CTA Container */}
        <div
          className="w-full max-w-[1142px] mx-auto flex flex-col lg:flex-row items-center relative lg:pl-16 overflow-hidden rounded-3xl bg-slate-50 dark:bg-[#090d16] border border-slate-200/60 dark:border-white/5 shadow-[0_12px_40px_rgba(0,0,0,0.03)] dark:shadow-none"
          style={{ minHeight: '472px' }}
        >

          {/* Blue glow background at top right - INSIDE container */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#0052ff]/15 rounded-full blur-[100px] -translate-y-1/3 translate-x-1/3 pointer-events-none" />

          {/* Left Side: Call to action copy */}
          <div className="lg:w-[45%] relative z-10 text-left pt-12 lg:pt-[76px] px-4 md:px-8 lg:px-0 lg:pl-[44px] pb-12 lg:pb-[76px] flex flex-col gap-6">
            <h2 className="text-[clamp(1.75rem,4vw,2.75rem)] font-semibold tracking-normal leading-[1.2] text-[#222222] dark:text-white transition-colors duration-300">
              Build powerful AI chatbots <br className="hidden sm:block" />
              for your website in <br className="hidden sm:block" />
              minutes.
            </h2>
            <p className="text-[#888888] dark:text-slate-400 text-base sm:text-lg leading-relaxed max-w-[90%] font-medium transition-colors duration-300">
              Try our no-code chatbot builder to automate conversations, support customers, and capture leads effortlessly.
            </p>
            <div className="pt-2">
              <Button
                className="!bg-[#0052ff] hover:!bg-[#003ecc] !text-white px-8 py-6 rounded-xl text-base font-bold border-none transition-all shadow-[0_8px_20px_rgba(13,83,252,0.2)]"
                onClick={() => alert("Registration and setup workflow is launching...")}
              >
                Get Started
              </Button>
            </div>
          </div>

          {/* Right Side: Dashboard Image */}
          <div className="lg:w-[55%] relative z-10 w-full h-full flex justify-end items-end self-end pt-8 lg:pt-0">
            <div className="relative w-full max-w-[680px] translate-x-4 lg:translate-x-16 translate-y-4 lg:translate-y-12 overflow-hidden rounded-3xl">
              <Image
                src="/images/image%201.png"
                alt="Dashboard Preview"
                width={3492}
                height={2270}
                className="w-full h-auto object-contain rounded-3xl shadow-[-10px_-10px_40px_rgba(0,0,0,0.06)] dark:shadow-none"
              />
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
