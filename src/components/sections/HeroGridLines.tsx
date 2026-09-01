 "use client";

import React from "react";

/** Background mesh grid only — no side rails or text frames */
export default function HeroGridLines() {
  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden"
      aria-hidden
    >
      <div className="hero-grid-mesh" />
    </div>
  );
}
