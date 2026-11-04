// Send QA pairing codes to the real CLI through hidden stdin only.
import { spawn } from "node:child_process";
let input = "";
if (process.stdin.isTTY) process.stdin.setRawMode(true);
process.stdin.setEncoding("utf8");
process.stdout.write("Ready for remote QA JSON on stdin (input is hidden).\n");
process.stdin.on("data", chunk => {
  input += chunk;
  const end = input.search(/[\r\n]/);
  if (end < 0) return;
  let rooms;
  try { rooms = JSON.parse(input.slice(0, end)); }
  catch { process.stderr.write("Invalid QA rooms.\n"); process.exit(1); }
  input = "";
  if (process.stdin.isTTY) process.stdin.setRawMode(false);
  process.stdin.pause();
  const root = "C:/Users/Administrator/Desktop/Alpha-Captcha-AI";
  const child = spawn(root + "/.venv/Scripts/python.exe", ["scripts/run_remote_engine.py", "--execute", "--once", "--rooms-stdin", "--base-url", "http://127.0.0.1:5186", "--device", "cuda", "--output", "runs/remote-booth-browser-v1"], {
    cwd: root, env: { ...process.env, PYTHONUTF8: "1" },
    stdio: ["pipe", "inherit", "inherit"], windowsHide: true,
  });
  child.stdin.end(JSON.stringify(rooms) + "\n");
  rooms = undefined;
  child.on("exit", code => process.exit(code ?? 1));
});
