"use client";

import React from "react";

export default function Footer() {
  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    if (id === "#") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const element = document.querySelector(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  const footerLinks = {
    Product: [
      { name: "Features", href: "#features" },
      { name: "Solutions", href: "#" }
    ],
    Company: [
      { name: "About us", href: "#" },
      { name: "Career", href: "#" }
    ],
    Resources: [
      { name: "Docs", href: "#" },
      { name: "Blog", href: "#" }
    ],
    Social: [
      { name: "x.com", href: "https://x.com" },
      { name: "LinkedIn", href: "https://linkedin.com" }
    ]
  };

  return (
    <footer className="w-full bg-white dark:bg-transparent flex justify-center transition-colors duration-300">
      <div className="w-full max-w-[1440px] mx-auto pt-[80px] pb-[32px] px-6 lg:px-[128px] flex flex-col md:flex-row gap-10 md:gap-20 justify-between">
        
        {/* Logo & Description */}
        <div className="flex flex-col space-y-4">
          <a
            href="#"
            className="inline-flex items-center gap-1 group transition-opacity hover:opacity-90"
            onClick={(e) => handleScrollTo(e, "#")}
          >
            <img
              src="/Synq1.svg"
              alt="SYNQDOC Logo"
              className="h-[36px] w-auto shrink-0 object-contain transition-transform duration-200 group-hover:scale-105"
            />
            <span className="text-3xl font-black tracking-tighter text-slate-900 dark:text-white leading-none">
              SYN<span className="text-[#0D53FC]">Q</span>DOC
            </span>
          </a>
          <p className="text-[15px] text-[#888888] dark:text-slate-400 font-medium leading-relaxed max-w-sm transition-colors duration-300">
            Chat as if you are talking to a human
          </p>
        </div>

        {/* Links Columns */}
        <div className="flex flex-wrap sm:flex-nowrap gap-10 sm:gap-16 lg:gap-[80px]">
          {(Object.keys(footerLinks) as Array<keyof typeof footerLinks>).map((category) => (
            <div key={category} className="flex flex-col space-y-5">
              <h4 className="text-[15px] font-medium text-[#0052ff]">
                {category}
              </h4>
              <ul className="space-y-3.5">
                {footerLinks[category].map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.href}
                      onClick={
                        link.href.startsWith("#")
                          ? (e) => handleScrollTo(e, link.href)
                          : undefined
                      }
                      className="text-[15px] text-[#888888] dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors font-medium duration-300"
                    >
                      {link.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

      </div>
    </footer>
  );
}
