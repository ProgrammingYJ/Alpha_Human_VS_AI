// Local QA only: hidden stdin -> a trusted child process environment/stdin.
// Credentials are never written to a file or passed as command arguments.
import { spawn } from "node:child_process";

let pending = "";
let child;
if (process.stdin.isTTY) process.stdin.setRawMode(true);
process.stdin.setEncoding("utf8");
process.stdout.write("Ready for booth QA JSON on stdin (input is hidden).\n");
process.stdin.on("data", (chunk) => {
  if (child) return;
  pending += chunk;
  const newline = pending.search(/[\r\n]/);
  if (newline < 0) return;
  let settings;
  try {
    settings = JSON.parse(pending.slice(0, newline));
    if (typeof settings.adminKey !== "string" || settings.adminKey.length < 24 || !Array.isArray(settings.argv) || settings.argv.some((x) => typeof x !== "string") || !settings.argv.length) throw new Error();
  } catch { process.stderr.write("Invalid QA settings; no secret logged.\n"); process.exit(1); }
  pending = "";
  if (process.stdin.isTTY) process.stdin.setRawMode(false);
  process.stdin.pause();
  const [command, ...args] = settings.argv;
  child = spawn(command, args, { cwd: settings.cwd || process.cwd(),
    env: { ...process.env, ALPHA_ADMIN_KEY: settings.adminKey, ALPHA_BASE_URL: settings.baseUrl || "http://127.0.0.1:5186" },
    stdio: ["pipe", "inherit", "inherit"], windowsHide: true });
  child.stdin.end(settings.adminKey + "\n");
  settings = undefined;
  child.on("exit", (code) => process.exit(code ?? 1));
});
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => { child?.kill(); process.exit(0); });
