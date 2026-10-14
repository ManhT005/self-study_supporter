import type { NextRequest } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const origin = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";
  const headers = new Headers();
  for (const key of ["content-type", "cookie", "origin"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const body =
      request.method === "GET" ? undefined : await request.arrayBuffer();
    if (body && body.byteLength > 21 * 1024 * 1024)
      return Response.json(
        {
          code: "too_large",
          message: "Tệp vượt quá giới hạn 20 MB.",
          request_id: crypto.randomUUID(),
        },
        { status: 413 },
      );
    const upstream = await fetch(
      `${origin}/api/${path.map(encodeURIComponent).join("/")}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(600_000),
      },
    );
    const resultHeaders = new Headers({ "Cache-Control": "no-store" });
    for (const key of ["content-type", "set-cookie", "x-request-id"]) {
      const value = upstream.headers.get(key);
      if (value) resultHeaders.set(key, value);
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: resultHeaders,
    });
  } catch {
    return Response.json(
      {
        code: "api_unavailable",
        message: "Không thể kết nối dịch vụ. Vui lòng thử lại.",
        request_id: crypto.randomUUID(),
      },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST };
