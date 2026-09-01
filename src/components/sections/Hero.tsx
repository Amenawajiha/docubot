"use client";

import Image from "next/image";
import React from "react";
import HeroGridLines from "@/components/sections/HeroGridLines";

/** Same horizontal grid as `Header` — 1440px cap, 120px gutters at xl */
const HERO_GUTTERS =
  "mx-auto w-full max-w-[1440px] px-4 sm:px-6 md:px-12 lg:px-20 xl:px-[120px]";

const HERO_PREVIEW_SRC = "/images/image%201.png";

const PREVIEW_IMG_WIDTH = 3492;
const PREVIEW_IMG_HEIGHT = 2270;

export default function Hero() {
  const handleScrollTo = (id: string) => {
    const element = document.querySelector(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section
      className="relative w-full overflow-x-hidden pb-0 pt-[120px] sm:pt-[140px] md:pt-[160px] lg:pt-[192px] hero-gradient transition-colors duration-300"
    >
      <HeroGridLines />

      <div
        className={`relative z-10 flex flex-col items-center gap-[42px] ${HERO_GUTTERS}`}
      >
        <div className="w-full max-w-[873px] text-center">
          <div className="mx-auto flex max-w-[764px] flex-col items-center space-y-5 sm:space-y-6 md:space-y-7">
            <h1 className="w-full text-balance text-center text-[clamp(2.25rem,6vw,3.75rem)] font-bold leading-[110%] tracking-[0] text-[#FFFFFF]">
              Turn Your Documents Into Intelligent Chatbots
            </h1>
            <p className="text-pretty text-sm leading-relaxed text-white/90 sm:text-base md:text-lg">
              Upload any PDF, DOCX, or website — SYNQDOC AI trains a custom
              chatbot on your content in minutes. No code required.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-1 sm:gap-4 sm:pt-2">
              <button
                type="button"
                className="cursor-pointer rounded-full bg-white px-7 py-3 text-sm font-bold text-[#0052ff] shadow-sm transition-all hover:bg-slate-50"
                onClick={() => handleScrollTo("#demo")}
              >
                Watch Demo
              </button>
              <button
                type="button"
                className="cursor-pointer rounded-full border border-white/80 bg-transparent px-7 py-3 text-sm font-bold text-white transition-all hover:bg-white/10"
                onClick={() => handleScrollTo("#cta")}
              >
                Start for free
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard mockup — blends into white as gradient opens below */}
        <div className="relative z-20 w-full max-w-[873px] shrink-0 overflow-hidden rounded-2xl bg-white shadow-[0_16px_48px_-20px_rgba(15,45,120,0.12)] sm:rounded-3xl transition-colors duration-300">
          <Image
            src={HERO_PREVIEW_SRC}
            alt="SYNQDOC AI interface preview"
            width={PREVIEW_IMG_WIDTH}
            height={PREVIEW_IMG_HEIGHT}
            priority
            sizes="(max-width: 873px) 100vw, 873px"
            className="block h-auto w-full align-middle"
          />
        </div>
      </div>
    </section>
  );
}
