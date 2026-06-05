import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Proxy logout through Next.js so we can clear the cookie server-side.
 */
export async function POST(req: NextRequest) {
  const token = req.cookies.get("ecc_token")?.value;

  // Tell backend to clear its cookie too (best-effort)
  if (token) {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      headers: { Cookie: `ecc_token=${token}` },
    }).catch(() => {});
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.delete("ecc_token");
  return response;
}
