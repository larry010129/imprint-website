import { NextResponse } from "next/server";

/** Render health check for the Next edge service (not under /api — that rewrites to FastAPI). */
export async function GET() {
  return NextResponse.json({ ok: true, service: "imprint-web" });
}
