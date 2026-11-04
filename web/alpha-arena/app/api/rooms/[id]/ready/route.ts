import { readyRoom, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  return route(async () => readyRoom(request, (await context.params).id));
}
