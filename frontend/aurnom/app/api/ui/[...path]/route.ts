import { NextRequest } from "next/server";

const EVENNIA_BASE_URL = process.env.EVENNIA_BASE_URL ?? "http://evennia:4001";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = new URL(`/ui/${path.join("/")}`, EVENNIA_BASE_URL);

  request.nextUrl.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });

  const response = await fetch(upstream.toString(), {
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
