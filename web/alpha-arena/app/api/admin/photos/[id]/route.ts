import { readAdminPhoto, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  return route(async () => readAdminPhoto(request, (await context.params).id));
}
