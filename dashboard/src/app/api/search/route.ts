import { getAllRawRecords } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = (searchParams.get("q") ?? "").toLowerCase().trim();

  if (!q) {
    return Response.json([]);
  }

  const all = getAllRawRecords();
  const results = all.filter((r) => {
    const text = `${r.value} ${r.brand} ${r.product} ${r.country} ${r.source} ${r.pillar}`.toLowerCase();
    return text.includes(q);
  });

  return Response.json(results.slice(0, 200));
}
