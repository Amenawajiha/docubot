import { NextResponse } from "next/server";

export async function GET() {
  const rawBackendUrl =
    process.env.INTERNAL_BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") ||
    "http://localhost:8001";
  
  // Force 127.0.0.1 on the server side to avoid Node.js IPv6 resolving issues
  const backendUrl = rawBackendUrl.replace("localhost", "127.0.0.1");

  let backendStatus: "up" | "down" = "down";

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(`${backendUrl}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      backendStatus = "up";
    }
  } catch {
    backendStatus = "down";
  }

  const isOk = backendStatus === "up";

  return NextResponse.json({
    status: isOk ? "ok" : "degraded",
    service: "docubot-frontend",
    backend: backendStatus,
    timestamp: new Date().toISOString(),
  });
}