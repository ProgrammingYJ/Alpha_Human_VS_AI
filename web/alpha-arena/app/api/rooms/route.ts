import { createRoom, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function POST(request: Request) { return route(() => createRoom(request)); }
