export const AUTH_KEY = "cv_auth";

export function checkCredentials(u: string, p: string) {
  return u === "admin" && p === "admin";
}

export function setSessionClient() {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_KEY, "true");
  // also set a non-HttpOnly cookie so middleware can definitely see it
  document.cookie = `${AUTH_KEY}=1; Path=/; Max-Age=2592000; SameSite=Lax`;
}

export function clearSessionClient() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_KEY);
  document.cookie = `${AUTH_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function isAuthenticated() {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(AUTH_KEY) === "true";
}
