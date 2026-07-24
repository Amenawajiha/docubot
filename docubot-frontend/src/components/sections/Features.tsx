"use client";

import React, { useState } from "react";
import { motion } from "motion/react";

const SECTION_GUTTERS =
  "mx-auto w-full max-w-[1440px] px-4 sm:px-6 md:px-12 lg:px-20 xl:px-[120px]";
const FEATURES_CONTENT =
  "mx-auto flex w-full max-w-[1200px] flex-col gap-16";
/** Figma row: 3×384px cards, 272px tall, 24px gap → 1200×864 grid */
const FEATURES_GRID =
  "grid w-full max-w-[1200px] grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-8 lg:grid-cols-3 lg:gap-[24px]";
/** Figma single card: 384×272, 16px radius, 24px padding, 24px internal gap */
const FEATURES_CARD =
  "box-border flex min-h-0 w-full flex-col gap-4 rounded-2xl border border-[#EAEAEA]/80 dark:border-[#222222] bg-white dark:bg-[#111111] p-6 shadow-[0_4px_24px_rgba(15,23,42,0.04)] transition-all duration-300 hover:shadow-[0_8px_32px_rgba(15,23,42,0.06)] hover:border-[#0052ff]/25 dark:hover:border-[#0052ff]/35 lg:min-h-[272px] lg:gap-[24px] lg:rounded-[16px] lg:p-[24px] cursor-pointer";

// Icon 1: Multi-Format Training
function TrainingIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 overflow-hidden shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Back page */}
        <motion.path
          d="M15 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4"
          animate={active ? { x: -1.5, y: -1, rotate: -4 } : { x: 0, y: 0, rotate: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        />
        {/* Front page */}
        <motion.path
          d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          animate={active ? { x: 1, y: 1, rotate: 4 } : { x: 0, y: 0, rotate: 0 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        />
        <path d="M14 2v6h6" />
        <line x1="8" y1="13" x2="16" y2="13" />
        <line x1="8" y1="17" x2="14" y2="17" />
      </motion.svg>
      {/* Scanning light sweeping */}
      {active && (
        <motion.div
          className="absolute left-0 right-0 h-[1.5px] bg-[#0052ff] shadow-[0_0_6px_#0052ff] z-10"
          animate={{ top: ["15%", "85%", "15%"] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
        />
      )}
    </div>
  );
}

// Icon 2: Full Customization
function CustomizationIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={active ? { rotate: [0, -10, 10, -5, 0] } : {}}
        transition={{ duration: 0.8, ease: "easeInOut" }}
      >
        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 14.7255 3.09032 17.1962 4.85857 19C5.32047 19.4754 5.28913 20.2449 4.7925 20.682C4.32185 21.0963 3.65584 21.1118 3.16729 20.7303C2.45781 20.1763 2 19.4442 2 18.5V17C2 15.3431 3.34315 14 5 14H6.5C7.32843 14 8 13.3284 8 12.5C8 12.2239 8.22386 12 8.5 12H9C10.6569 12 12 10.6569 12 9V8.5C12 8.22386 12.2239 8 12.5 8C13.3284 8 14 7.32843 14 6.5V5C14 3.34315 15.3431 2 17 2" className="opacity-40" />
        {/* Brush handle & head */}
        <motion.path
          d="M18 8L6 20"
          animate={active ? { x: [-0.5, 1, -0.5], y: [0.5, -1, 0.5] } : {}}
          transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
        />
        <motion.path
          d="M16 6l2 2"
          animate={active ? { x: [-0.5, 1, -0.5], y: [0.5, -1, 0.5] } : {}}
          transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
        />
        <motion.path
          d="M19 5a1.5 1.5 0 1 0-3-3 1.5 1.5 0 0 0 3 3z"
          fill="currentColor"
          animate={active ? { scale: [1, 1.25, 1] } : {}}
          transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
        />
      </motion.svg>
      {/* Micro paint drops */}
      {active && (
        <div className="absolute inset-0 pointer-events-none">
          <motion.span
            className="absolute top-2 left-3 w-1.5 h-1.5 rounded-full bg-violet-500"
            initial={{ scale: 0 }}
            animate={{ scale: [0, 1.2, 0], y: [0, 5] }}
            transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }}
          />
          <motion.span
            className="absolute bottom-3.5 right-3 w-1 h-1 rounded-full bg-emerald-500"
            initial={{ scale: 0 }}
            animate={{ scale: [0, 1.2, 0], x: [0, -3] }}
            transition={{ repeat: Infinity, duration: 1.5, delay: 0.7 }}
          />
        </div>
      )}
    </div>
  );
}

// Icon 3: WhatsApp Integration
function WhatsAppIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={active ? { scale: [1, 1.1, 1], rotate: [0, 4, -4, 0] } : {}}
        transition={{ duration: 0.6 }}
      >
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        <path d="M17 14c-.3-.1-1.7-.8-2-1-.3-.1-.5-.1-.7.2l-.8 1c-.2.2-.4.3-.7.1-1.3-.7-2.3-1.7-3-3-.2-.3-.1-.5.1-.7l1-.8c.3-.2.3-.4.2-.7l-1-2c-.1-.3-.3-.3-.5-.3h-.5c-.3 0-.7.1-1 .4-1.3 1.3-1.3 3.3.4 5.6 1.9 2.5 4.5 4.1 7.2 4.1.8 0 1.5-.1 2-.4.4-.3.7-.7.7-1v-.5c0-.2-.1-.4-.3-.5z" fill="currentColor" className="text-[#0052ff] dark:text-blue-400" />
      </motion.svg>
      {/* Wave ripples */}
      {active && (
        <>
          <motion.span
            className="absolute inset-0 rounded-xl border border-blue-500/25"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1.3, opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut" }}
          />
          <motion.span
            className="absolute inset-0 rounded-xl border border-blue-500/10"
            initial={{ scale: 1, opacity: 0.4 }}
            animate={{ scale: 1.55, opacity: 0 }}
            transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut", delay: 0.4 }}
          />
        </>
      )}
    </div>
  );
}

// Icon 4: Deep Analytics
function AnalyticsIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <svg className="w-5.5 h-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {/* Left bar */}
        <motion.rect
          x="3"
          y="11"
          width="4"
          height="9"
          rx="1"
          initial={{ height: 9, y: 11 }}
          animate={active ? { height: [9, 13, 6, 9], y: [11, 7, 14, 11] } : { height: 9, y: 11 }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        />
        {/* Middle bar */}
        <motion.rect
          x="10"
          y="4"
          width="4"
          height="16"
          rx="1"
          initial={{ height: 16, y: 4 }}
          animate={active ? { height: [16, 11, 17, 16], y: [4, 9, 3, 4] } : { height: 16, y: 4 }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut", delay: 0.25 }}
        />
        {/* Right bar */}
        <motion.rect
          x="17"
          y="8"
          width="4"
          height="12"
          rx="1"
          initial={{ height: 12, y: 8 }}
          animate={active ? { height: [12, 15, 8, 12], y: [8, 5, 12, 8] } : { height: 12, y: 8 }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut", delay: 0.5 }}
        />
      </svg>
    </div>
  );
}

// Icon 5: API & Integrations
function APIIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={active ? { rotate: 90 } : { rotate: 0 }}
        transition={{ duration: 0.45, ease: "easeInOut" }}
      >
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </motion.svg>
      {/* Node pulse details */}
      {active && (
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            className="absolute top-2.5 right-2.5 h-1.5 w-1.5 rounded-full bg-[#0052ff]"
            animate={{ scale: [1, 1.6, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.3 }}
          />
          <motion.div
            className="absolute bottom-2.5 left-2.5 h-1.5 w-1.5 rounded-full bg-[#0052ff]"
            animate={{ scale: [1, 1.6, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.3, delay: 0.65 }}
          />
        </div>
      )}
    </div>
  );
}

// Icon 6: Enterprise Security
function SecurityIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={active ? { scale: [1, 1.06, 1] } : {}}
        transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
      >
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <motion.path
          d="m9 11 2 2 4-4"
          initial={{ pathLength: 1 }}
          animate={active ? { pathLength: [0, 1] } : { pathLength: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </motion.svg>
    </div>
  );
}

// Icon 7: Multilingual Support
function MultilingualIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={active ? { rotate: 360 } : {}}
        transition={{ repeat: Infinity, duration: 16, ease: "linear" }}
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </motion.svg>
      {/* Floating letters */}
      {active && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center text-[7px] font-sans font-bold">
          <motion.span
            className="absolute top-1 right-2 text-[#0052ff]/80 dark:text-blue-300"
            animate={{ y: [-2, 2, -2], opacity: [0, 1, 0] }}
            transition={{ repeat: Infinity, duration: 2.2 }}
          >
            A
          </motion.span>
          <motion.span
            className="absolute bottom-1 left-2 text-[#0052ff]/80 dark:text-blue-300"
            animate={{ y: [2, -2, 2], opacity: [0, 1, 0] }}
            transition={{ repeat: Infinity, duration: 2.2, delay: 1.1 }}
          >
            あ
          </motion.span>
        </div>
      )}
    </div>
  );
}

// Icon 8: Live Chat Handoff
function HandoffIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <motion.svg
        className="w-5.5 h-5.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
        <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
        {/* Signal waves emitting */}
        <motion.path
          d="M12 8a3 3 0 0 1 3 3"
          initial={{ opacity: 0.3 }}
          animate={active ? { opacity: [0.3, 1, 0.3] } : {}}
          transition={{ repeat: Infinity, duration: 1.2 }}
        />
        <motion.path
          d="M12 5a6 6 0 0 1 6 6"
          initial={{ opacity: 0.1 }}
          animate={active ? { opacity: [0.1, 1, 0.1] } : {}}
          transition={{ repeat: Infinity, duration: 1.2, delay: 0.35 }}
        />
      </motion.svg>
    </div>
  );
}

// Icon 9: Human-Like Conversations
function ConversationsIcon({ active }: { active: boolean }) {
  return (
    <div className="relative h-12 w-12 flex items-center justify-center rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-100/50 dark:border-blue-900/10 text-[#0052ff] dark:text-blue-400 shrink-0">
      <svg className="w-5.5 h-5.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {/* Chat balloon */}
        <motion.path
          d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
          animate={active ? { y: [-1, 1, -1] } : {}}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        />
        {/* Chat dot markers */}
        {active && (
          <>
            <motion.circle
              cx="9"
              cy="10"
              r="1"
              fill="currentColor"
              animate={{ scale: [1, 1.6, 1] }}
              transition={{ repeat: Infinity, duration: 0.9, ease: "easeInOut", delay: 0.1 }}
            />
            <motion.circle
              cx="13"
              cy="10"
              r="1"
              fill="currentColor"
              animate={{ scale: [1, 1.6, 1] }}
              transition={{ repeat: Infinity, duration: 0.9, ease: "easeInOut", delay: 0.3 }}
            />
            <motion.circle
              cx="17"
              cy="10"
              r="1"
              fill="currentColor"
              animate={{ scale: [1, 1.6, 1] }}
              transition={{ repeat: Infinity, duration: 0.9, ease: "easeInOut", delay: 0.5 }}
            />
          </>
        )}
      </svg>
    </div>
  );
}

const FEATURES = [
  {
    title: "Multi-Format Training",
    description:
      "Upload PDFs, DOCX, TXT, CSV, HTML, or connect a website URL. Your bot learns from all sources seamlessly.",
  },
  {
    title: "Full Customization",
    description:
      "Change colors, logo, greeting message, and tone. White-label available on Business plans.",
  },
  {
    title: "WhatsApp Integration",
    description:
      "Connect your website directly with WhatsApp to enable instant customer communication and faster responses.",
  },
  {
    title: "Deep Analytics",
    description:
      "See what users ask, track resolution rates, identify knowledge gaps, and improve your content.",
  },
  {
    title: "API & Integrations",
    description:
      "Connect with Slack, WhatsApp, Zendesk, HubSpot, and 100+ tools via our REST API or Zapier.",
  },
  {
    title: "Enterprise Security",
    description:
      "SOC2 compliant, end-to-end data encryption, GDPR ready, SSO support, and private data hosting.",
  },
  {
    title: "Multilingual Support",
    description:
      "Automatically responds in the language your user speaks. Supports 80+ languages out of the box.",
  },
  {
    title: "Live Chat Handoff",
    description:
      "When the AI chatbot can't answer, escalate seamlessly to a human agent without losing conversation context.",
  },
  {
    title: "Human-Like Conversations",
    description:
      "Delivers responses that feel natural and human-like — with instant response times and zero wait.",
  },
] as const;

const ICON_MAP: Record<string, React.ComponentType<{ active: boolean }>> = {
  "Multi-Format Training": TrainingIcon,
  "Full Customization": CustomizationIcon,
  "WhatsApp Integration": WhatsAppIcon,
  "Deep Analytics": AnalyticsIcon,
  "API & Integrations": APIIcon,
  "Enterprise Security": SecurityIcon,
  "Multilingual Support": MultilingualIcon,
  "Live Chat Handoff": HandoffIcon,
  "Human-Like Conversations": ConversationsIcon,
};

function FeatureCard({
  title,
  description,
}: (typeof FEATURES)[number]) {
  const [isHovered, setIsHovered] = useState(false);
  const IconComponent = ICON_MAP[title];

  return (
    <article
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => setIsHovered(!isHovered)}
      className={FEATURES_CARD}
    >
      {IconComponent ? <IconComponent active={isHovered} /> : null}
      <h3 className="text-lg font-bold tracking-tight text-[#111111] dark:text-white lg:text-xl transition-colors duration-300">
        {title}
      </h3>
      <p className="text-sm leading-relaxed text-[#64748B] dark:text-slate-400 transition-colors duration-300">
        {description}
      </p>
    </article>
  );
}

export default function Features() {
  return (
    <section
      id="features"
      className="relative scroll-mt-[79px] bg-transparent pb-16 pt-16 md:pb-20 md:pt-20 xl:pb-[101px] xl:pt-[101px]"
    >
      <div className={SECTION_GUTTERS}>
        <div className={FEATURES_CONTENT}>
          <header className="mx-auto w-full max-w-3xl shrink-0 text-center">
            <span className="inline-flex rounded-full border border-[#0052ff]/30 bg-white dark:bg-slate-900/50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-[#0052ff] transition-colors duration-300">
              Features
            </span>
            <h2 className="mt-5 text-3xl font-extrabold tracking-tight text-[#111111] dark:text-white sm:text-4xl md:text-[2.75rem] md:leading-tight transition-colors duration-300">
              Everything You Need to Build Smarter Support
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-[#64748B] dark:text-slate-400 sm:text-base transition-colors duration-300">
              Powerful features that make deploying AI chatbots simple, effective,
              and reliable.
            </p>
          </header>

          <div className={FEATURES_GRID}>
            {FEATURES.map((feature) => (
              <FeatureCard key={feature.title} {...feature} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
