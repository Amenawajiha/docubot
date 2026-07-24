"use client";

import { Lightbulb } from "lucide-react";
import React from "react";
import PhotonBeam from "@/components/ui/photon-beam";

const SECTION_GUTTERS =
  "mx-auto w-full max-w-[1440px] px-4 sm:px-6 md:px-12 lg:px-20 xl:px-[120px]";
/** Figma stat card: 282×278, 16px radius */
const STAT_CARD =
  "box-border flex w-full flex-col overflow-hidden rounded-[16px] p-6 shadow-[0_4px_24px_rgba(15,23,42,0.05)] transition-shadow duration-200 lg:min-h-[278px] lg:p-[24px]";
const STATS_ROW =
  "mx-auto flex w-full max-w-[1200px] flex-col items-stretch gap-6 sm:grid sm:grid-cols-2 lg:grid lg:grid-cols-4 lg:items-start lg:gap-6";

const STATS = [
  {
    label: "Chatbots Deployed",
    value: "500K+",
    description:
      "Automating conversations for businesses across industries.",
    highlight: false,
  },
  {
    label: "Customer Queries Resolved",
    value: "2M+",
    description: "Instant responses delivered with accuracy and speed.",
    highlight: false,
  },
  {
    label: "Automation Accuracy",
    value: "95%",
    description:
      "AI-powered responses trained to understand real user intent.",
    highlight: true,
  },
  {
    label: "Integrations Available",
    value: "120+",
    description:
      "Connect seamlessly with your favorite tools and platforms.",
    highlight: false,
  },
] as const;

function SectionWaveBg() {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden opacity-50 dark:opacity-100">
      <div className="absolute -top-16 -left-[10%] w-[100%] h-full">
        <PhotonBeam
          colorBg="transparent"
          colorLine="#0052ff"
          colorSignal="#00d9ff"
          useColor2={true}
          colorSignal2="#0052ff"
          useColor3={true}
          colorSignal3="#00b8d4"
          lineCount={75}
          spreadHeight={50}
          signalCount={85}
          speedGlobal={0.345}
          trailLength={3}
          bloomStrength={3.0}
          bloomRadius={0.5}
        />
      </div>
      <div className="absolute -top-16 -right-[10%] w-[100%] h-full scale-x-[-1]">
        <PhotonBeam
          colorBg="transparent"
          colorLine="#0052ff"
          colorSignal="#00d9ff"
          useColor2={true}
          colorSignal2="#0052ff"
          useColor3={true}
          colorSignal3="#00b8d4"
          lineCount={75}
          spreadHeight={50}
          signalCount={85}
          speedGlobal={0.345}
          trailLength={3}
          bloomStrength={3.0}
          bloomRadius={0.5}
        />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  description,
  highlight,
  staggerDown,
}: (typeof STATS)[number] & { staggerDown: boolean }) {
  return (
    <article
      className={`${STAT_CARD} relative ${staggerDown ? "lg:mt-14" : "lg:mt-0"
        } ${highlight
          ? "z-10 bg-[#0052ff] text-white shadow-[0_12px_40px_rgba(13,83,252,0.28)] dark:shadow-[0_12px_40px_rgba(13,83,252,0.4)]"
          : "border border-[#EAEAEA] dark:border-[#222222] bg-white dark:bg-[#111111]"
        }`}
    >
      <div className="relative z-10 flex h-full flex-col">
        <div className="flex items-center gap-2.5">
          <span
            className={`h-2 w-2 shrink-0 rounded-full transition-colors duration-300 ${highlight ? "bg-white" : "bg-[#0052ff]"
              }`}
          />
          <span
            className={`text-sm font-semibold transition-colors duration-300 ${highlight ? "text-white/95" : "text-[#64748B] dark:text-slate-400"
              }`}
          >
            {label}
          </span>
        </div>

        <p
          className={`mt-5 text-[2.5rem] font-extrabold leading-none tracking-tight lg:mt-6 lg:text-[2.75rem] transition-colors duration-300 ${highlight ? "text-white" : "text-[#111111] dark:text-white"
            }`}
        >
          {value}
        </p>

        <hr
          className={`mt-5 border-0 border-t lg:mt-6 transition-colors duration-300 ${highlight ? "border-white/25" : "border-[#E8ECF2] dark:border-[#333333]"
            }`}
        />

        <div className="mt-4 flex flex-1 items-end justify-between gap-4 lg:mt-5">
          <p
            className={`max-w-[200px] text-sm leading-relaxed transition-colors duration-300 ${highlight ? "text-white/90" : "text-[#64748B] dark:text-slate-400"
              }`}
          >
            {description}
          </p>
          <Lightbulb
            className={`h-[22px] w-[22px] shrink-0 stroke-[1.75] transition-colors duration-300 ${highlight ? "text-white/75" : "text-[#C5CED9] dark:text-slate-500"
              }`}
            aria-hidden
          />
        </div>
      </div>
    </article>
  );
}

export default function WhyChooseUs() {
  return (
    <section
      id="why-choose-us"
      className="relative scroll-mt-[79px] bg-transparent py-20 md:py-24 lg:py-28 overflow-hidden transition-colors duration-300"
    >
      <SectionWaveBg />
      <div className={`${SECTION_GUTTERS} relative z-10`}>
        <header className="mx-auto mb-14 max-w-3xl text-center md:mb-20 lg:mb-24">
          <span className="inline-flex rounded-full border border-[#0052ff]/30 bg-white dark:bg-slate-900/50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#0052ff] transition-colors duration-300">
            Why to choose us
          </span>
          <h2 className="mt-5 text-3xl font-extrabold leading-[1.12] tracking-tight text-[#111111] dark:text-white sm:text-4xl md:text-[2.75rem] transition-colors duration-300">
            Revolutionizing Customer Support With Intelligent Chatbots
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[#64748B] dark:text-slate-400 sm:text-base transition-colors duration-300">
            Step into the future of automation. Our AI-powered chatbot builder
            helps businesses create smart, responsive, and personalized
            conversations that improve customer experience and save time.
          </p>
        </header>

        <div className="relative w-full">
          <div className={`${STATS_ROW} relative z-10`}>
            {STATS.map((stat, index) => (
              <StatCard
                key={stat.label}
                {...stat}
                staggerDown={index % 2 === 1}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
