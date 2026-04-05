import { getAllRawRecords } from "@/lib/data";

export async function GET() {
  const records = getAllRawRecords();
  return Response.json(records);
}
