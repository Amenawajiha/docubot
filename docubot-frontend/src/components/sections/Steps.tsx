"use client";

import { ArrowRight } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";

const SECTION_GUTTERS =
  "mx-auto w-full max-w-[1440px] px-4 sm:px-6 md:px-12 lg:px-20 xl:px-[120px]";

const STEP_CYCLE_MS = 3200;

function useStepsFlow(revealed: boolean) {
  const [activeStep, setActiveStep] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (!revealed || isPaused) return;

    const interval = window.setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 4);
    }, STEP_CYCLE_MS);

    return () => window.clearInterval(interval);
  }, [revealed, isPaused]);

  return { activeStep, setActiveStep, isPaused, setIsPaused };
}

function StepOneIllustration({ active }: { active: boolean }) {
  return (
    <div className="relative flex h-36 w-full max-w-[220px] items-center justify-center rounded-2xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 p-4 overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(13,83,252,0.05),transparent)] opacity-80 pointer-events-none" />

      {/* Floating File Cards */}
      <div className="relative flex items-center justify-center w-full h-full">
        {/* Card 3 (Back URL Card) */}
        <motion.div
          className="absolute w-[120px] h-[70px] rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 p-2 shadow-sm flex flex-col justify-between"
          animate={active ? {
            y: [-12, -16, -12],
            x: [-15, -15, -15],
            rotate: [-6, -4, -6]
          } : { y: -12, x: -15, rotate: -6 }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        >
          <div className="flex items-center gap-1.5">
            <div className="h-3.5 w-3.5 rounded-full bg-blue-500/10 flex items-center justify-center">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            </div>
            <span className="text-[7px] font-mono text-zinc-400">https://url...</span>
          </div>
          <div className="h-1.5 w-14 rounded bg-zinc-150 dark:bg-zinc-800" />
          <div className="h-1.5 w-8 rounded bg-zinc-150 dark:bg-zinc-800" />
        </motion.div>

        {/* Card 2 (Middle Doc Card) */}
        <motion.div
          className="absolute w-[120px] h-[75px] rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/90 p-2 shadow-md flex flex-col justify-between"
          animate={active ? {
            y: [4, 8, 4],
            x: [15, 15, 15],
            rotate: [6, 8, 6]
          } : { y: 4, x: 15, rotate: 6 }}
          transition={{ repeat: Infinity, duration: 3.4, ease: "easeInOut", delay: 0.2 }}
        >
          <div className="flex items-center gap-1.5">
            <span className="text-[8px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1 rounded">XLS</span>
            <span className="text-[7px] font-mono text-zinc-500 dark:text-zinc-400">pricing.xlsx</span>
          </div>
          <div className="space-y-1.5">
            <div className="h-1.5 w-full rounded bg-zinc-205 dark:bg-zinc-800" />
            <div className="h-1.5 w-12 rounded bg-zinc-205 dark:bg-zinc-800" />
          </div>
        </motion.div>

        {/* Card 1 (Front PDF Card) */}
        <motion.div
          className="absolute w-[130px] h-[85px] rounded-xl border border-zinc-350 dark:border-zinc-700 bg-white dark:bg-zinc-950 p-2.5 shadow-lg flex flex-col justify-between z-10"
          animate={active ? {
            y: [-4, 0, -4],
            x: [0, 0, 0]
          } : { y: -4, x: 0 }}
          transition={{ repeat: Infinity, duration: 2.8, ease: "easeInOut" }}
        >
          <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-1.5">
            <div className="flex items-center gap-1.5">
              <span className="text-[8px] font-bold text-red-655 dark:text-red-400 bg-red-500/10 px-1 rounded">PDF</span>
              <span className="text-[8px] font-semibold text-zinc-700 dark:text-zinc-300">knowledge.pdf</span>
            </div>
            <span className="text-[6px] font-mono text-zinc-400">1.8 MB</span>
          </div>
          <div className="space-y-1.5 my-1.5">
            <div className="h-1.5 w-full rounded bg-zinc-100 dark:bg-zinc-800" />
            <div className="h-1.5 w-[90%] rounded bg-zinc-100 dark:bg-zinc-800" />
            <div className="h-1.5 w-[75%] rounded bg-zinc-100 dark:bg-zinc-800" />
          </div>
        </motion.div>

        {/* Active Laser Scanning Overlay */}
        {active && (
          <>
            <motion.div
              className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#0052ff] to-transparent shadow-[0_0_10px_rgba(13,83,252,0.8)] z-20"
              animate={{ top: ["12%", "88%", "12%"] }}
              transition={{ repeat: Infinity, duration: 2.2, ease: "easeInOut" }}
            />
            {/* Glowing Scan Particles */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none z-20">
              {[...Array(4)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute h-1.5 w-1.5 rounded-full bg-blue-500/75"
                  initial={{ x: 60 + i * 28, y: 110, opacity: 0 }}
                  animate={{
                    y: [110, 10],
                    opacity: [0, 1, 1, 0],
                    scale: [1, 1.2, 0.7],
                  }}
                  transition={{
                    repeat: Infinity,
                    duration: 1.8,
                    delay: i * 0.35,
                    ease: "easeOut",
                  }}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StepTwoIllustration({ active }: { active: boolean }) {
  const [statusIndex, setStatusIndex] = useState(0);
  const statuses = [
    "Reading sources...",
    "Extracting text content...",
    "Generating embeddings...",
    "Indexing vector database...",
    "Knowledge Base Ready!"
  ];

  useEffect(() => {
    if (!active) {
      const handle = setTimeout(() => setStatusIndex(0), 0);
      return () => clearTimeout(handle);
    }
    const timer = setInterval(() => {
      setStatusIndex((prev) => (prev + 1) % statuses.length);
    }, 700);
    return () => clearInterval(timer);
  }, [active, statuses.length]);

  return (
    <div className="relative flex h-36 w-full max-w-[220px] flex-col items-center justify-center rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 p-3 overflow-hidden">
      <div className="relative flex items-center justify-center flex-1 w-full">
        {/* Animated Dashed Outer Ring */}
        <motion.div
          className="absolute w-22 h-22 rounded-full border border-dashed border-[#0052ff]/30 flex items-center justify-center"
          animate={active ? { rotate: 360 } : {}}
          transition={{ repeat: Infinity, duration: 15, ease: "linear" }}
        >
          {/* Orbital glowing satellite */}
          <motion.div
            className="absolute -top-1 left-1/2 h-2.5 w-2.5 -ml-1.25 rounded-full bg-[#0052ff] shadow-[0_0_8px_#0052ff]"
            animate={active ? { scale: [1, 1.3, 1] } : {}}
            transition={{ repeat: Infinity, duration: 1.5 }}
          />
        </motion.div>

        {/* Neural Network Nodes */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <svg className="absolute inset-0 w-full h-full stroke-zinc-200/70 dark:stroke-zinc-800/70" strokeWidth="1">
            <line x1="45" y1="35" x2="100" y2="60" className={active ? "stroke-[#0052ff]/30 duration-1000 animate-pulse" : ""} />
            <line x1="175" y1="35" x2="100" y2="60" className={active ? "stroke-[#0052ff]/30 duration-1000 animate-pulse" : ""} />
            <line x1="45" y1="85" x2="100" y2="60" className={active ? "stroke-[#0052ff]/30 duration-1000 animate-pulse" : ""} />
            <line x1="175" y1="85" x2="100" y2="60" className={active ? "stroke-[#0052ff]/30 duration-1000 animate-pulse" : ""} />
          </svg>

          {/* Peripheral Node 1 */}
          <motion.div
            className="absolute left-8 top-6 h-4 w-4 rounded-full border border-zinc-200 dark:border-zinc-805 bg-white dark:bg-zinc-950 flex items-center justify-center shadow-sm"
            animate={active ? { scale: [1, 1.15, 1], borderColor: ["#e4e4e7", "#0052ff", "#e4e4e7"] } : {}}
            transition={{ repeat: Infinity, duration: 2.2, delay: 0.1 }}
          >
            <div className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          </motion.div>

          {/* Peripheral Node 2 */}
          <motion.div
            className="absolute right-8 top-6 h-4 w-4 rounded-full border border-zinc-200 dark:border-zinc-805 bg-white dark:bg-zinc-950 flex items-center justify-center shadow-sm"
            animate={active ? { scale: [1, 1.15, 1], borderColor: ["#e4e4e7", "#0052ff", "#e4e4e7"] } : {}}
            transition={{ repeat: Infinity, duration: 2.4, delay: 0.3 }}
          >
            <div className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          </motion.div>

          {/* Peripheral Node 3 */}
          <motion.div
            className="absolute left-8 bottom-6 h-4 w-4 rounded-full border border-zinc-200 dark:border-zinc-805 bg-white dark:bg-zinc-950 flex items-center justify-center shadow-sm"
            animate={active ? { scale: [1, 1.15, 1], borderColor: ["#e4e4e7", "#0052ff", "#e4e4e7"] } : {}}
            transition={{ repeat: Infinity, duration: 1.8, delay: 0.2 }}
          >
            <div className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          </motion.div>

          {/* Peripheral Node 4 */}
          <motion.div
            className="absolute right-8 bottom-6 h-4 w-4 rounded-full border border-zinc-200 dark:border-zinc-805 bg-white dark:bg-zinc-950 flex items-center justify-center shadow-sm"
            animate={active ? { scale: [1, 1.15, 1], borderColor: ["#e4e4e7", "#0052ff", "#e4e4e7"] } : {}}
            transition={{ repeat: Infinity, duration: 2.6, delay: 0.4 }}
          >
            <div className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700" />
          </motion.div>
        </div>

        {/* Central Database Core */}
        <motion.div
          className="relative z-10 w-12 h-12 rounded-xl border border-blue-500 bg-white dark:bg-zinc-950 flex items-center justify-center shadow-[0_0_20px_rgba(13,83,252,0.1)] dark:shadow-[0_0_20px_rgba(13,83,252,0.25)]"
          animate={active ? {
            boxShadow: ["0 0 15px rgba(13,83,252,0.1)", "0 0 25px rgba(13,83,252,0.4)", "0 0 15px rgba(13,83,252,0.1)"],
            scale: [1, 1.06, 1]
          } : {}}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        >
          <svg className="w-5.5 h-5.5 text-[#0052ff] dark:text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
          </svg>
        </motion.div>
      </div>

      {/* Dynamic Status Text Indicator */}
      <div className="w-full text-center z-10 mt-1">
        <span
          className={`inline-flex items-center gap-1 border border-blue-100 dark:border-blue-900/40 bg-blue-50/50 dark:bg-blue-950/20 px-2 py-0.5 rounded text-[9px] font-mono font-semibold text-blue-600 dark:text-blue-400 transition-all duration-300 ${active ? "opacity-100 scale-100" : "opacity-50 scale-95"
            }`}
        >
          {active && <span className="h-1 w-1 rounded-full bg-blue-500 animate-ping" />}
          {statuses[statusIndex]}
        </span>
      </div>
    </div>
  );
}

function StepThreeIllustration({ active }: { active: boolean }) {
  const colors = [
    { name: "Blue", primary: "#0052ff", secondary: "#E8F0FF", text: "#FFFFFF" },
    { name: "Purple", primary: "#7C3AED", secondary: "#F5F3FF", text: "#FFFFFF" },
    { name: "Emerald", primary: "#059669", secondary: "#ECFDF5", text: "#FFFFFF" }
  ];
  const [colorIdx, setColorIdx] = useState(0);

  useEffect(() => {
    if (!active) {
      const handle = setTimeout(() => setColorIdx(0), 0);
      return () => clearTimeout(handle);
    }
    const timer = setInterval(() => {
      setColorIdx((prev) => (prev + 1) % colors.length);
    }, 1000);
    return () => clearInterval(timer);
  }, [active, colors.length]);

  const activeColor = colors[colorIdx];

  return (
    <div className="relative flex h-36 w-full max-w-[220px] flex-col rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-2 overflow-hidden shadow-sm">
      {/* Mini Chat Widget Mockup */}
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-900 pb-1.5 px-1">
        <div className="flex items-center gap-1.5">
          <div
            className="w-4 h-4 rounded-full flex items-center justify-center text-[7px] text-white font-bold transition-colors duration-500"
            style={{ backgroundColor: activeColor.primary }}
          >
            B
          </div>
          <div>
            <div className="text-[8px] font-bold text-zinc-800 dark:text-zinc-200">Bot Assistant</div>
            <div className="text-[6px] text-zinc-400 font-mono">online</div>
          </div>
        </div>
        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-1.5 p-1 px-1.5 overflow-hidden">
        {/* User Message */}
        <div className="flex justify-end">
          <div className="rounded-lg bg-zinc-100 dark:bg-zinc-800 text-[6.5px] p-1.5 max-w-[80%] text-zinc-700 dark:text-zinc-300">
            What are your options?
          </div>
        </div>

        {/* AI Message */}
        <div className="flex justify-start items-end gap-1">
          <div className="w-3.5 h-3.5 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center text-[6px] font-bold">🤖</div>
          <div
            className="rounded-lg text-[6.5px] p-1.5 max-w-[80%] transition-colors duration-500"
            style={{
              backgroundColor: activeColor.primary,
              color: activeColor.text
            }}
          >
            I can be customized instantly to match your brand style!
          </div>
        </div>
      </div>

      {/* Color Select Footer */}
      <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-900 pt-1.5 px-1 mt-1">
        <span className="text-[6px] text-zinc-400 font-bold uppercase tracking-wider">Brand Tone</span>
        <div className="flex gap-1 relative">
          {colors.map((c, idx) => (
            <div
              key={c.name}
              className={`w-3.5 h-3.5 rounded-full cursor-pointer flex items-center justify-center transition-all duration-300 ${colorIdx === idx ? "ring-2 ring-offset-1 ring-blue-500 scale-110" : "scale-90 opacity-60"
                }`}
              style={{ backgroundColor: c.primary }}
            />
          ))}

          {/* Animated Cursor selecting the color themes */}
          {active && (
            <motion.div
              className="absolute z-20 pointer-events-none text-zinc-900 dark:text-zinc-100"
              initial={{ x: 60, y: 15 }}
              animate={{
                x: [60, -32, -14, 4, 60],
                y: [15, 0, 0, 0, 15]
              }}
              transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 drop-shadow-[0_1px_2px_rgba(0,0,0,0.4)]">
                <path d="M4.5 3v15.25l3.8-3.8 2.2 4.85 2.1-1-2.2-4.85 5.1-.2z" />
              </svg>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

function StepFourIllustration({ active }: { active: boolean }) {
  const codeText = `<script src="widget.js" />`;
  const [typedText, setTypedText] = useState("");

  useEffect(() => {
    if (!active) {
      const handle = setTimeout(() => setTypedText(""), 0);
      return () => clearTimeout(handle);
    }
    let idx = 0;
    const interval = setInterval(() => {
      setTypedText(codeText.slice(0, idx + 1));
      idx++;
      if (idx >= codeText.length) {
        clearInterval(interval);
      }
    }, 85);
    return () => clearInterval(interval);
  }, [active, codeText]);

  return (
    <div className="relative flex h-36 w-full max-w-[220px] flex-col rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 p-2 overflow-hidden">
      {/* Code Snippet Box */}
      <div className="w-full rounded-lg bg-zinc-950 dark:bg-black p-2 border border-zinc-900 font-mono text-[7px] text-zinc-400 flex flex-col justify-between h-[48px] shadow-inner relative">
        <div className="flex items-center justify-between border-b border-zinc-900 pb-1 mb-1">
          <div className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500/80" />
            <span className="h-1.5 w-1.5 rounded-full bg-yellow-500/80" />
            <span className="h-1.5 w-1.5 rounded-full bg-green-500/80" />
          </div>
          <span className="text-[5px] text-zinc-700">embed.html</span>
        </div>
        <div className="flex-1 flex items-center">
          <span className="text-zinc-650 mr-1 select-none">1</span>
          <span className="text-blue-400 font-semibold font-mono">
            {typedText}
            {active && (
              <motion.span
                className="inline-block w-0.5 h-2.5 bg-blue-500 ml-0.5"
                animate={{ opacity: [1, 0, 1] }}
                transition={{ repeat: Infinity, duration: 0.6 }}
              />
            )}
          </span>
        </div>
      </div>

      {/* Visual Beam */}
      {active && (
        <motion.div
          className="absolute left-1/2 w-0.5 bg-gradient-to-b from-[#0052ff] to-cyan-400 z-20 shadow-[0_0_8px_#0052ff]"
          initial={{ top: 48, height: 0 }}
          animate={{ height: [0, 38, 0], top: [48, 48, 86] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
        />
      )}

      {/* Website Mockup */}
      <div className="flex-1 mt-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm overflow-hidden flex flex-col relative">
        <div className="bg-zinc-100 dark:bg-zinc-900 h-2 px-1 flex items-center border-b border-zinc-150 dark:border-zinc-850">
          <div className="h-1 w-6 rounded bg-zinc-200 dark:bg-zinc-800" />
        </div>

        <div className="flex-1 p-1.5 space-y-1">
          <div className="h-1 w-14 rounded bg-zinc-100 dark:bg-zinc-800" />
          <div className="h-1 w-18 rounded bg-zinc-150 dark:bg-zinc-800" />
          <div className="h-1 w-10 rounded bg-zinc-150 dark:bg-zinc-800" />
        </div>

        {/* Launcher Button */}
        <div className="absolute bottom-1 right-1.5 z-10">
          <motion.div
            className="w-4 h-4 rounded-full bg-[#0052ff] flex items-center justify-center text-[7px] text-white shadow-md relative"
            animate={active ? { scale: [1, 1.25, 1] } : {}}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
          >
            💬

            {active && (
              <>
                <span className="absolute -inset-1.5 rounded-full border border-blue-500/40 animate-ping opacity-75 pointer-events-none" />
                <span className="absolute -inset-3 rounded-full border border-blue-500/25 animate-ping [animation-delay:0.4s] opacity-55 pointer-events-none" />
              </>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

const STEPS = [
  {
    label: "Step One",
    title: "Upload Document",
    description:
      "Upload PDFs, Word files, URLs, or paste raw text. Supports 50+ file formats.",
    Illustration: StepOneIllustration,
  },
  {
    label: "Step Two",
    title: "Auto-Training",
    description:
      "Our AI reads and indexes your content, building a knowledge base in seconds.",
    Illustration: StepTwoIllustration,
  },
  {
    label: "Step Three",
    title: "Customize",
    description:
      "Set your bot's name, avatar, colors, and personality to match your brand.",
    Illustration: StepThreeIllustration,
  },
  {
    label: "Step Four",
    title: "Embed & Go Live",
    description:
      "Copy one line of code to embed on your website. Or share a direct chat link.",
    Illustration: StepFourIllustration,
  },
] as const;

function StepArrow({
  revealed,
  flowActive,
  delayMs,
}: {
  revealed: boolean;
  flowActive: boolean;
  delayMs: number;
}) {
  return (
    <div
      className={`hidden shrink-0 items-center justify-center self-center lg:flex h-9 transition-all duration-500 ${revealed ? "steps-arrow-enter" : "opacity-0"
        }`}
      style={{ animationDelay: `${delayMs}ms` }}
      aria-hidden
    >
      <div className="relative flex items-center">
        {/* Glowing laser line */}
        <div className="w-8 h-[2px] bg-zinc-200 dark:bg-zinc-800 rounded relative overflow-hidden">
          {flowActive && (
            <motion.div
              className="absolute left-0 top-0 bottom-0 w-4 bg-gradient-to-r from-transparent via-[#0052ff] to-transparent shadow-[0_0_8px_#0052ff]"
              animate={{ left: ["-50%", "150%"] }}
              transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
            />
          )}
        </div>
        {/* Glow arrow frame */}
        <div className={`ml-1 flex h-7 w-7 items-center justify-center rounded-full border transition-all duration-300 ${flowActive
            ? "bg-[#E8F0FF] dark:bg-blue-950/60 border-[#0052ff]/30 scale-110 shadow-sm"
            : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800"
          }`}>
          <ArrowRight className={`h-3 w-3 stroke-[2.5] transition-colors duration-300 ${flowActive ? "text-[#0052ff] dark:text-blue-400" : "text-zinc-400 dark:text-zinc-600"
            }`} />
        </div>
      </div>
    </div>
  );
}

interface StepCardProps {
  label: string;
  title: string;
  description: string;
  Illustration: React.ComponentType<{ active: boolean }>;
  index: number;
  revealed: boolean;
  isActive: boolean;
  activeStep: number;
  isPaused: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onClick: () => void;
}

function StepCard({
  label,
  title,
  description,
  Illustration,
  index,
  revealed,
  isActive,
  activeStep,
  isPaused,
  onMouseEnter,
  onMouseLeave,
  onClick,
}: StepCardProps) {
  return (
    <article
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={onClick}
      className={`group/card flex min-h-[350px] flex-1 flex-col rounded-[24px] border p-6 md:p-7 cursor-pointer relative overflow-hidden transition-all duration-500 ${revealed ? "steps-card-enter" : "opacity-0"
        } ${isActive
          ? "bg-white dark:bg-zinc-950 border-[#0052ff]/35 shadow-[0_16px_48px_rgba(13,83,252,0.14)] dark:border-[#0052ff]/40 dark:shadow-[0_16px_48px_rgba(13,83,252,0.18)]"
          : "bg-white/70 dark:bg-zinc-950/40 border-zinc-200/80 dark:border-zinc-900 shadow-[0_4px_24px_rgba(15,23,42,0.02)] hover:border-zinc-300 dark:hover:border-zinc-850"
        }`}
      style={{ animationDelay: `${index * 180}ms` }}
    >
      {/* Glow Effect when active */}
      {isActive && (
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(13,83,252,0.04),transparent)] opacity-80 pointer-events-none" />
      )}

      {/* Progress bar line at the top */}
      <div className="w-full h-[3px] bg-zinc-100 dark:bg-zinc-900 rounded-full overflow-hidden mb-6">
        <motion.div
          key={`${activeStep}-${isPaused}-${isActive}`}
          className="h-full bg-[#0052ff] origin-left"
          initial={{
            width: isActive && !isPaused
              ? "0%"
              : (isActive && isPaused ? "100%" : (index < activeStep ? "100%" : "0%"))
          }}
          animate={{ width: isActive ? "100%" : (index < activeStep ? "100%" : "0%") }}
          transition={
            isActive && !isPaused
              ? { duration: STEP_CYCLE_MS / 1000, ease: "linear" }
              : { duration: 0.3, ease: "easeInOut" }
          }
        />
      </div>

      <p
        className={`text-xs font-bold uppercase tracking-wider transition-colors duration-300 ${isActive ? "text-[#0052ff] dark:text-blue-400" : "text-zinc-400 dark:text-zinc-600"
          }`}
      >
        {label}
      </p>
      <h3 className="mt-1 text-lg font-bold tracking-tight text-[#111111] dark:text-white md:text-xl transition-colors duration-300">
        {title}
      </h3>

      <div className="flex flex-1 items-center justify-center py-6 md:py-8 select-none">
        <Illustration active={isActive} />
      </div>

      <p className="text-xs leading-relaxed text-[#64748B] dark:text-slate-400 transition-colors duration-300">
        {description}
      </p>
    </article>
  );
}

export default function Steps() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
        }
      },
      { threshold: 0.15 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const { activeStep, setActiveStep, isPaused, setIsPaused } = useStepsFlow(revealed);

  return (
    <section
      id="how-it-works"
      className="relative scroll-mt-[79px] bg-transparent py-20 md:py-24 lg:py-28"
    >
      <div className={SECTION_GUTTERS}>
        <header className="mx-auto mb-12 max-w-3xl text-center md:mb-16">
          <span className="inline-flex rounded-full border border-[#0052ff]/30 bg-white dark:bg-slate-900/50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#0052ff] transition-colors duration-300">
            How it works
          </span>
          <h2 className="mx-auto mt-5 max-w-4xl text-center text-[clamp(1.75rem,5vw,2.75rem)] font-extrabold leading-[1.12] tracking-tight text-[#111111] dark:text-white transition-colors duration-300">
            From Document to
            <br />
            Chatbot in 4 Steps
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-center text-sm leading-relaxed text-[#64748B] dark:text-slate-400 sm:text-base transition-colors duration-300">
            No technical skills required. Get your AI-powered assistant live in
            under 2
            <br />
            minutes.
          </p>
        </header>

        {/* Responsive Grid of Cards */}
        <div ref={containerRef} className="flex flex-col gap-6 lg:flex-row lg:items-stretch lg:gap-3">
          {STEPS.map((step, index) => (
            <React.Fragment key={step.label}>
              <StepCard
                {...step}
                index={index}
                revealed={revealed}
                isActive={activeStep === index}
                activeStep={activeStep}
                isPaused={isPaused}
                onMouseEnter={() => {
                  setActiveStep(index);
                  setIsPaused(true);
                }}
                onMouseLeave={() => {
                  setIsPaused(false);
                }}
                onClick={() => {
                  setActiveStep(index);
                  setIsPaused(true);
                }}
              />
              {index < STEPS.length - 1 && (
                <StepArrow
                  revealed={revealed}
                  flowActive={activeStep === index + 1}
                  delayMs={index * 180 + 120}
                />
              )}
            </React.Fragment>
          ))}
        </div>


      </div>
    </section>
  );
}
