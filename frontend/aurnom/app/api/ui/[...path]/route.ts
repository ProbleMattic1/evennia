import { NextRequest } from "next/server";

const EVENNIA_BASE_URL = process.env.EVENNIA_BASE_URL ?? "http://evennia:4001";
const UPSTREAM_FETCH_TIMEOUT_MS = 60_000;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

/** Prefer end-client IP for Evennia's ip_from_request (OriginIpMiddleware). */
function buildProxyHeaders(request: NextRequest, cookie: string): Record<string, string> {
  const headers: Record<string, string> = {};
  if (cookie) {
    headers.cookie = cookie;
  }
  const authz = request.headers.get("authorization");
  if (authz) {
    headers.authorization = authz;
  }
  const xff = request.headers.get("x-forwarded-for");
  if (xff) {
    headers["x-forwarded-for"] = xff;
    return headers;
  }
  const realIp = request.headers.get("x-real-ip");
  if (realIp) {
    headers["x-real-ip"] = realIp;
    headers["x-forwarded-for"] = realIp.trim();
    return headers;
  }
  return headers;
}

function buildUpstreamUrl(request: NextRequest, path: string[]) {
  const upstream = new URL(`/ui/${path.join("/")}`, EVENNIA_BASE_URL);
  request.nextUrl.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });
  return upstream;
}

function buildResponseHeaders(upstream: Response): Record<string, string> {
  const headers: Record<string, string> = {
    "content-type": upstream.headers.get("content-type") ?? "application/json",
  };
  const setCookie = upstream.headers.get("set-cookie");
  if (setCookie) {
    headers["set-cookie"] = setCookie;
  }
  return headers;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = buildUpstreamUrl(request, path);
  const cookie = request.headers.get("cookie") ?? "";
  try {
    const response = await fetch(upstream.toString(), {
      cache: "no-store",
      headers: buildProxyHeaders(request, cookie),
      signal: AbortSignal.timeout(UPSTREAM_FETCH_TIMEOUT_MS),
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: buildResponseHeaders(response),
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return new Response(JSON.stringify({ ok: false, error: "upstream_fetch_failed", detail }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = buildUpstreamUrl(request, path);
  const cookie = request.headers.get("cookie") ?? "";
  const contentType = request.headers.get("content-type") ?? "application/json";
  try {
    const response = await fetch(upstream.toString(), {
      method: "POST",
      headers: {
        "content-type": contentType,
        ...buildProxyHeaders(request, cookie),
      },
      body: await request.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_FETCH_TIMEOUT_MS),
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: buildResponseHeaders(response),
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return new Response(JSON.stringify({ ok: false, error: "upstream_fetch_failed", detail }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
}
