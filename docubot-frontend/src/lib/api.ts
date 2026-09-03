const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

interface FetchOptions extends RequestInit {
  requireAuth?: boolean;
}

export async function fetchApi(endpoint: string, options: FetchOptions = {}) {
  const { requireAuth = true, headers: customHeaders, ...rest } = options;

  const headers = new Headers(customHeaders);
  
  if (!headers.has("Content-Type") && !(rest.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      ...rest,
      credentials: "include",
      headers,
    });
  } catch (netErr) {
    console.warn(`[fetchApi] Network error connecting to ${BASE_URL}${endpoint}:`, netErr);
    return new Response(
      JSON.stringify({ detail: "Backend server is unreachable or offline." }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }

  // Handle 401 Unauthorized by attempting to refresh the token (skip for auth endpoints)
  const isAuthEndpoint = endpoint.startsWith("/auth/login") || endpoint.startsWith("/auth/register") || endpoint.startsWith("/auth/refresh");
  if (response.status === 401 && requireAuth && !isAuthEndpoint) {
    try {
      const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });

      if (refreshRes.ok) {
        // Retry original request with new cookies
        try {
          response = await fetch(`${BASE_URL}${endpoint}`, {
            ...rest,
            credentials: "include",
            headers,
          });
        } catch {
          return new Response(
            JSON.stringify({ detail: "Backend server became unreachable during retry." }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          );
        }
      } else {
        // Refresh failed, user must log in again
        localStorage.removeItem("isLoggedIn");
        if (typeof window !== "undefined") {
          window.location.href = "/";
        }
      }
    } catch (err) {
      console.error("Failed to refresh token", err);
      localStorage.removeItem("isLoggedIn");
      if (typeof window !== "undefined") {
        window.location.href = "/";
      }
    }
  }

  return response;
}
