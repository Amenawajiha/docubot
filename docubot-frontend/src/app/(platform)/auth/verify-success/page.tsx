"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function VerifySuccessPage() {
  const router = useRouter();

  useEffect(() => {
    localStorage.setItem("isLoggedIn", "true");
    
    // Notify other tabs/components
    window.dispatchEvent(new Event("storage"));
    
    // Redirect to dashboard
    router.push("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200">
      <div className="text-center space-y-4">
        <h2 className="text-2xl font-bold">Verifying Email...</h2>
        <p className="text-sm text-slate-500">Please wait while we redirect you to your dashboard.</p>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      </div>
    </div>
  );
}
