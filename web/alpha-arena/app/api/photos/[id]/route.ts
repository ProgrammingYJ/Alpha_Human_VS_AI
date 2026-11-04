import { readPhoto, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  return route(async () => readPhoto((await context.params).id));
}
