// Receive a development-only admin secret on hidden stdin, never argv or a file.
import { spawn } from "node:child_process";

let pending = "";
let child;
if (process.stdin.isTTY) process.stdin.setRawMode(true);
process.stdin.setEncoding("utf8");
process.stdout.write("Ready for local preview JSON on stdin (input is hidden).\n");
process.stdin.on("data", (chunk) => {
  if (child) return;
  pending += chunk;
  const newline = pending.search(/[\r\n]/);
  if (newline < 0) return;
  let adminKey;
  try {
    const settings = JSON.parse(pending.slice(0, newline));
    adminKey = settings.adminKey;
    if (typeof adminKey !== "string" || adminKey.length < 24) throw new Error("missing key");
  } catch {
    process.stderr.write("Invalid preview settings; secret was not logged.\n");
    process.exit(1);
  }
  pending = "";
  if (process.stdin.isTTY) process.stdin.setRawMode(false);
  process.stdin.pause();
  child = spawn(process.execPath, ["scripts/run-framework.mjs", "dev", "--port", "5186", "--hostname", "127.0.0.1"], {
    cwd: process.cwd(), env: { ...process.env, ALPHA_LOCAL_ADMIN_KEY: adminKey },
    stdio: ["ignore", "inherit", "inherit"], windowsHide: true,
  });
  adminKey = undefined;
  child.on("exit", (code) => process.exit(code ?? 1));
});
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => {
  child?.kill();
  process.exit(0);
});
