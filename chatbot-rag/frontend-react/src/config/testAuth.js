// Test authentication utilities
// NOTE: This token is for local development and testing only. Do NOT use in production.

// Single, non-expiring-for-90-days test token (dev only). Replace with VITE_TEST_JWT for local env.
const FALLBACK_TEST_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMSIsImV4cCI6MTc3NDY3OTMwMCwidG9rZW5fdXNhZ2UiOiJhY2Nlc3MifQ.weFqGdeAKFD7JR5BWBROtGjAHbNgttCuH_2ftdJqENI";

export const TEST_JWT = import.meta.env.VITE_TEST_JWT ?? FALLBACK_TEST_JWT;

/**
 * Helper that returns development test JWT information.
 * In production, ensure tokens are issued by your auth service instead.
 */
export const getTestJwt = () => ({
  token: TEST_JWT,
});
