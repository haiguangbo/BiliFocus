import { NextRequest, NextResponse } from "next/server";

const ALLOWED_HOSTS = new Set(["i0.hdslb.com", "i1.hdslb.com", "i2.hdslb.com"]);
const BILIBILI_REFERER = "https://www.bilibili.com/";
const USER_AGENT =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36";

export async function GET(request: NextRequest) {
  const src = request.nextUrl.searchParams.get("src");
  if (!src) {
    return new NextResponse("missing src", { status: 400 });
  }

  let target: URL;
  try {
    target = new URL(src);
  } catch {
    return new NextResponse("invalid src", { status: 400 });
  }

  if (target.protocol !== "https:" || !ALLOWED_HOSTS.has(target.hostname)) {
    return new NextResponse("unsupported src", { status: 400 });
  }

  const upstream = await fetch(target, {
    headers: {
      Referer: BILIBILI_REFERER,
      Origin: "https://www.bilibili.com",
      "User-Agent": USER_AGENT,
    },
    cache: "force-cache",
  });

  if (!upstream.ok) {
    return new NextResponse("upstream image unavailable", { status: upstream.status });
  }

  const contentType = upstream.headers.get(`content-type`) ?? "image/jpeg";
  const cacheControl = upstream.headers.get("cache-control") ?? "public, max-age=3600";
  const body = await upstream.arrayBuffer();

  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": cacheControl,
    },
  });
}
