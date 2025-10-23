import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { username, password } = await req.json();
  if (username !== "admin" || password !== "admin") {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  // HttpOnly cookie for server (middleware) to trust
  res.headers.append(
    "Set-Cookie",
    "cv_auth=1; Path=/; Max-Age=2592000; SameSite=Lax; HttpOnly"
  );
  return res;
}
