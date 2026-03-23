import { NextRequest } from "next/server";

const EVENNIA_BASE_URL = process.env.EVENNIA_BASE_URL ?? "http://evennia:4001";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function buildUpstreamUrl(request: NextRequest, path: string[]) {
  const upstream = new URL(`/ui/${path.join("/")}`, EVENNIA_BASE_URL);
  request.nextUrl.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });
  return upstream;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = buildUpstreamUrl(request, path);

  const cookie = request.headers.get("cookie") ?? "";

  const response = await fetch(upstream.toString(), {
    cache: "no-store",
    headers: cookie ? { cookie } : {},
  });

  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = buildUpstreamUrl(request, path);

  const cookie = request.headers.get("cookie") ?? "";

  const response = await fetch(upstream.toString(), {
    method: "POST",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
      ...(cookie ? { cookie } : {}),
    },
    body: await request.text(),
    cache: "no-store",
  });

  const body = await response.text();

  return new Response(body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
