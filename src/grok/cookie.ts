export function normalizeSsoToken(token: string): string {
  const trimmed = String(token ?? "").trim();
  if (!trimmed) return "";
  return trimmed.startsWith("sso=") ? trimmed.slice(4).trim() : trimmed;
}

export function buildAuthCookie(token: string, cfCookie: string): string {
  const normalized = normalizeSsoToken(token);
  const base = `sso-rw=${normalized};sso=${normalized}`;
  const cf = String(cfCookie ?? "").trim();
  if (!cf) return base;
  return `${base};${cf}`;
}

