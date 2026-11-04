declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    ADMIN_KEY?: string;
    ADMIN_OWNER_ID?: string;
  }
}
