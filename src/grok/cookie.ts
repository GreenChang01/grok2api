export function normalizeSsoToken(token: string): string {
  const trimmed = String(token ?? "").trim();
  if (!trimmed) return "";

  const fromCookie = (key: string): string => {
    const m = trimmed.match(new RegExp(`(?:^|;\\s*)${key}=([^;]+)`));
    return m?.[1]?.trim() ?? "";
  };

  const bySso = fromCookie("sso");
  if (bySso) return bySso;

  const bySsoRw = fromCookie("sso-rw");
  if (bySsoRw) return bySsoRw;

  if (trimmed.startsWith("sso=")) {
    const value = trimmed.slice(4).trim();
    const cut = value.indexOf(";");
    return (cut >= 0 ? value.slice(0, cut) : value).trim();
  }

  if (trimmed.startsWith("sso-rw=")) {
    const value = trimmed.slice("sso-rw=".length).trim();
    const cut = value.indexOf(";");
    return (cut >= 0 ? value.slice(0, cut) : value).trim();
  }

  return trimmed;
}

export function buildAuthCookie(token: string, cfCookie: string): string {
  const normalized = normalizeSsoToken(token);
  const base = `sso-rw=${normalized};sso=${normalized}`;
  const cf = String(cfCookie ?? "").trim();
  if (!cf) return base;
  return `${base};${cf}`;
}
