import { NextResponse } from "next/server";

export async function GET() {
  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") ||
    "http://127.0.0.1:8001";

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