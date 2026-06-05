import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Proxy /auth/me through Next.js so the ecc_token cookie (set on localhost:3000)
 * is forwarded server-side to the FastAPI backend.
 *
 * This avoids the cross-origin cookie problem: browsers won't reliably send
 * a localhost:3000 cookie to localhost:8000 in cross-origin XHR, but a
 * Next.js server-side fetch CAN read the cookie from req.cookies and forward
 * it explicitly in the Authorization/Cookie header.
 */
export async function GET(req: NextRequest) {
  const token = req.cookies.get("ecc_token")?.value;

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const resp = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Cookie: `ecc_token=${token}` },
  });

  if (!resp.ok) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const user = await resp.json();
  return NextResponse.json(user);
}
