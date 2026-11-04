// Local test secrets stay in hidden stdin and child environment only.
import { spawn } from "node:child_process";
let pending = "";
if (process.stdin.isTTY) process.stdin.setRawMode(true);
process.stdin.setEncoding("utf8");
process.stdout.write("Ready for local audit JSON on stdin (input is hidden).\n");
process.stdin.on("data", chunk => {
  pending += chunk;
  const newline = pending.search(/[\r\n]/);
  if (newline < 0) return;
  let config;
  try {
    config = JSON.parse(pending.slice(0, newline));
    if (typeof config.adminKey !== "string" || config.adminKey.length < 24) throw new Error();
    if (!Array.isArray(config.files) || config.files.some(file => !/^server\/[a-z.-]+\.test\.mjs$/.test(file))) throw new Error();
  } catch { process.stderr.write("Invalid audit settings; no secret logged.\n"); process.exit(1); }
  pending = "";
  if (process.stdin.isTTY) process.stdin.setRawMode(false);
  process.stdin.pause();
  const child = spawn(process.execPath, ["--test", ...config.files], {
    cwd: "C:/Users/Administrator/Desktop/Alpha-Captcha-AI/web/alpha-arena",
    env: { ...process.env, ALPHA_BASE_URL: "http://127.0.0.1:5186", ALPHA_ADMIN_KEY: config.adminKey },
    stdio: ["ignore", "inherit", "inherit"], windowsHide: true,
  });
  config = undefined;
  child.on("exit", code => process.exit(code ?? 1));
});
