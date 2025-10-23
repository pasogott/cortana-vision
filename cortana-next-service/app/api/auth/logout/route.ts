import { NextResponse } from "next/server";

export async function POST() {
  const res = NextResponse.json({ ok: true });
  res.headers.append("Set-Cookie", "cv_auth=; Path=/; Max-Age=0; SameSite=Lax; HttpOnly");
  return res;
}
