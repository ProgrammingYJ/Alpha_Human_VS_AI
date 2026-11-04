import { activatePhotoBank, adminPhotos, uploadPhoto, route } from "@/server/service";
export const dynamic = "force-dynamic";
export async function GET(request: Request) { return route(() => adminPhotos(request)); }
export async function POST(request: Request) { return route(() => uploadPhoto(request)); }
export async function PUT(request: Request) { return route(() => activatePhotoBank(request)); }
