import type { GrokSettings } from "../settings";

const DEFAULT_GROK_BASE = "https://grok.com";
const DEFAULT_ASSET_BASE = "https://assets.grok.com";

function parseBaseUrl(raw: string): URL | null {
  const value = String(raw ?? "").trim();
  if (!value) return null;

  try {
    return new URL(value);
  } catch {
    try {
      return new URL(`https://${value}`);
    } catch {
      return null;
    }
  }
}

function normalizeBaseUrl(raw: string, fallback: string): URL {
  const parsed = parseBaseUrl(raw);
  if (parsed) {
    parsed.hash = "";
    parsed.search = "";
    parsed.pathname = parsed.pathname.replace(/\/+$/, "");
    return parsed;
  }
  return new URL(fallback);
}

function normalizePath(pathOrUrl: string): string {
  const value = String(pathOrUrl ?? "").trim();
  if (!value) return "/";
  if (value.startsWith("http://") || value.startsWith("https://")) {
    try {
      const u = new URL(value);
      return `${u.pathname || "/"}${u.search || ""}`;
    } catch {
      return "/";
    }
  }
  if (value.startsWith("?")) return `/${value}`;
  return value.startsWith("/") ? value : `/${value}`;
}

function joinBaseAndPath(base: URL, pathOrUrl: string): string {
  const path = normalizePath(pathOrUrl);
  const noTrailing = base.pathname.replace(/\/+$/, "");
  const basePrefix = noTrailing === "/" ? "" : noTrailing;
  return `${base.origin}${basePrefix}${path}`;
}

export function buildGrokApiUrl(settings: GrokSettings, pathOrUrl: string): string {
  const base = normalizeBaseUrl(settings.proxy_url ?? "", DEFAULT_GROK_BASE);
  return joinBaseAndPath(base, pathOrUrl);
}

export function buildAssetApiUrl(settings: GrokSettings, pathOrUrl: string): string {
  const base = normalizeBaseUrl(settings.cache_proxy_url ?? settings.proxy_url ?? "", DEFAULT_ASSET_BASE);
  return joinBaseAndPath(base, pathOrUrl);
}

