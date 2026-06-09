import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const resp = await fetch(`${API_BASE}/api/v1/auth/admin-login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    return NextResponse.json({ detail: "Invalid admin credentials" }, { status: 401 });
  }

  const user = await resp.json();

  // Forward the ecc_token cookie from backend to browser
  const setCookies = resp.headers.getSetCookie();
  const eccTokenEntry = setCookies.find((c) => c.startsWith("ecc_token="));
  const eccTokenValue = eccTokenEntry?.split(";")[0].split("=").slice(1).join("=");

  const response = NextResponse.json(user);
  if (eccTokenValue) {
    response.cookies.set("ecc_token", eccTokenValue, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 8 * 60 * 60,
    });
  }
  return response;
}
