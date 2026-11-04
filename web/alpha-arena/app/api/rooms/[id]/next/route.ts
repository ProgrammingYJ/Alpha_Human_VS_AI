import { nextParticipant, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return route(() => nextParticipant(request, id));
}
