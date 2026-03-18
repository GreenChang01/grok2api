import type { GrokSettings } from "../settings";
import { getDynamicHeaders } from "./headers";
import { toRateLimitModel } from "./models";
import { buildGrokApiUrl } from "./upstream";

const RATE_LIMIT_API_PATH = "/rest/rate-limits";

export async function checkRateLimits(
  cookie: string,
  settings: GrokSettings,
  model: string,
): Promise<Record<string, unknown> | null> {
  const rateModel = toRateLimitModel(model);
  const headers = getDynamicHeaders(settings, RATE_LIMIT_API_PATH);
  headers.Cookie = cookie;
  const body = JSON.stringify({ requestKind: "DEFAULT", modelName: rateModel });

  const resp = await fetch(buildGrokApiUrl(settings, RATE_LIMIT_API_PATH), { method: "POST", headers, body });
  if (!resp.ok) return null;
  return (await resp.json()) as Record<string, unknown>;
}
