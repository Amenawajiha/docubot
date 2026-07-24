"use client";

import React, { useRef, useEffect, useState } from "react";

export default function Testimonials() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);

  const testimonials = [
    {
      quote: "DocuBot AI has cut our customer support load by 65% in less than two weeks. The training process took just 30 seconds after uploading our FAQ files.",
      name: "Marcus Aurelius",
      role: "Head of Operations",
      company: "Trajan Logistics",
      avatar: "MA",
      color: "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
    },
    {
      quote: "Being able to automate responses in multiple languages solved a huge expansion blocker for us. Our clients get instant help in Spanish, German, and French.",
      name: "Sarah Jenkins",
      role: "Customer Experience Manager",
      company: "Webflow Studio",
      avatar: "SJ",
      color: "bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
    },
    {
      quote: "The direct API webhooks let our chatbot look up real-time delivery statuses from our database. It's a complete game changer for our e-commerce store.",
      name: "Daniel Kovacs",
      role: "VP of Product",
      company: "Cartflow Inc.",
      avatar: "DK",
      color: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
    }
  ];

  const activeIndexRef = useRef(0);

  const scrollToCard = (index: number) => {
    if (scrollRef.current) {
      const container = scrollRef.current;
      const card = container.children[index] as HTMLElement;
      if (card) {
        container.scrollTo({
          left: index === 0 ? 0 : card.offsetLeft - 8,
          behavior: "smooth",
        });
      }
    }
  };

  useEffect(() => {
    if (isPaused) return;

    const interval = setInterval(() => {
      activeIndexRef.current = (activeIndexRef.current + 1) % testimonials.length;
      scrollToCard(activeIndexRef.current);
    }, 4000);

    return () => clearInterval(interval);
  }, [isPaused, testimonials.length]);

  const handleScroll = (dir: "left" | "right") => {
    if (dir === "left") {
      activeIndexRef.current = (activeIndexRef.current - 1 + testimonials.length) % testimonials.length;
    } else {
      activeIndexRef.current = (activeIndexRef.current + 1) % testimonials.length;
    }
    scrollToCard(activeIndexRef.current);
  };

  return (
    <section id="testimonials" className="py-20 md:py-28 bg-white dark:bg-transparent scroll-mt-12 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Column: Heading and Large Quote */}
          <div className="lg:col-span-5 space-y-6">
            <span className="text-8xl font-serif text-[#0052ff] opacity-15 leading-none block -mb-8">
              ““
            </span>
            <span className="inline-flex text-xs font-bold text-[#0052ff] border border-[#0052ff]/20 px-3.5 py-1.5 rounded-full uppercase tracking-wider bg-slate-50 dark:bg-slate-900/50 transition-colors duration-300">
              Testimonials
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white tracking-tight transition-colors duration-300">
              What our clients say
            </h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm sm:text-base leading-relaxed transition-colors duration-300">
              Read how companies are automating support, improving response times, and increasing user satisfaction with DocuBot.
            </p>

            {/* Slider Navigation Buttons */}
            <div className="flex space-x-3 pt-2">
              <button
                onClick={() => handleScroll("left")}
                className="w-11 h-11 rounded-full border border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 transition-all cursor-pointer"
                aria-label="Previous testimonial"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
              <button
                onClick={() => handleScroll("right")}
                className="w-11 h-11 rounded-full border border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 transition-all cursor-pointer"
                aria-label="Next testimonial"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          </div>

          {/* Right Column: Snap Slider Cards */}
          <div className="lg:col-span-7 relative">
            <div
              ref={scrollRef}
              className="relative flex space-x-6 overflow-x-auto scrollbar-none snap-x snap-mandatory py-4 px-2"
              style={{ scrollbarWidth: "none" }}
              onMouseEnter={() => setIsPaused(true)}
              onMouseLeave={() => setIsPaused(false)}
              onTouchStart={() => setIsPaused(true)}
              onTouchEnd={() => setIsPaused(false)}
            >
              {testimonials.map((t, idx) => (
                <div
                  key={idx}
                  className="flex-shrink-0 w-full sm:w-[360px] snap-start bg-white dark:bg-[#111111] border border-[#EAEAEA] dark:border-[#222222] rounded-3xl p-6 md:p-8 flex flex-col justify-between shadow-sm hover:shadow-md transition-all duration-300 space-y-6"
                >
                  <p className="text-slate-700 dark:text-slate-300 text-sm md:text-base leading-relaxed italic transition-colors duration-300">
                    &ldquo;{t.quote}&rdquo;
                  </p>
                  
                  {/* User Profile */}
                  <div className="flex items-center space-x-3.5 pt-4 border-t border-slate-100 dark:border-slate-800 transition-colors duration-300">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors duration-300 ${t.color}`}>
                      {t.avatar}
                    </div>
                    <div className="text-xs transition-colors duration-300">
                      <p className="font-extrabold text-slate-900 dark:text-white transition-colors duration-300">{t.name}</p>
                      <p className="text-slate-400 font-medium transition-colors duration-300">
                        {t.role}, <span className="text-[#0052ff]">{t.company}</span>
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
