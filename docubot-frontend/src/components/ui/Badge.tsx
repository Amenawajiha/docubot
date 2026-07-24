import React from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "outline" | "success";
  children: React.ReactNode;
}

export function Badge({
  variant = "primary",
  className = "",
  children,
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border transition-all duration-300";

  const variantStyles = {
    primary:
      "bg-indigo-500/10 text-indigo-300 border-indigo-500/25 shadow-[0_0_10px_rgba(99,102,241,0.05)]",
    secondary:
      "bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_10px_rgba(6,182,212,0.05)]",
    outline: "bg-transparent text-slate-400 border-slate-700",
    success: "bg-emerald-500/10 text-emerald-300 border-emerald-500/25",
  };

  return (
    <span
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
