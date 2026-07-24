"use client";

import React from "react";

export default function DemoVideo() {
  return (
    <section id="demo" className="py-20 md:py-28 bg-transparent">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-12 md:mb-16 space-y-4">
          <span className="inline-flex text-xs font-bold text-[#0052ff] border border-[#0052ff]/30 px-3.5 py-1.5 rounded-full uppercase tracking-wider bg-white dark:bg-slate-900/50 transition-colors duration-300">
            Product Demo
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight transition-colors duration-300">
            See Our Chatbot Builder In Action
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm sm:text-base leading-relaxed transition-colors duration-300">
            Build and customize your chatbot, test answers in real time, and deploy in seconds.
          </p>
        </div>

        {/* Video Player Card */}
        <div className="mx-auto relative group w-full max-w-[945px]">
          <div 
            className="bg-black border-[#EAEAEA] overflow-hidden shadow-2xl relative flex items-center justify-center"
            style={{
              aspectRatio: '945/504',
              borderRadius: '17.5px',
              borderWidth: '7.88px',
              opacity: 1
            }}
          >
            <video
              src="/images/vedios/Chat Bot Development.webm"
              autoPlay
              muted
              loop
              playsInline
              className="absolute inset-0 w-full h-full object-cover"
            />
          </div>
        </div>

      </div>
    </section>
  );
}
