import { adminStatus, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function GET(request: Request) { return route(() => adminStatus(request)); }
