import { arenaHealth, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function GET() { return route(arenaHealth); }
