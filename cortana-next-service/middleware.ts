import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE = "cv_auth";

export function middleware(req: NextRequest) {
  const p = req.nextUrl.pathname;
  if (p === "/login" || p.startsWith("/api/") || p.startsWith("/_next/") || p === "/favicon.ico" || p.startsWith("/public/")) {
    return NextResponse.next();
  }
  const authed = req.cookies.get(AUTH_COOKIE)?.value === "1";
  if (!authed) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", p);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/:path*"] };
