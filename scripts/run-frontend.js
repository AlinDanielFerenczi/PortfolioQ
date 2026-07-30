// Spawns Vite's own JS entrypoint directly via node.exe instead of going
// through "npm run dev --prefix frontend". On Windows, npm resolves to
// npm.cmd -- a real batch file -- and Ctrl+C on a subprocess that's a .cmd
// file triggers Windows' "Terminate batch job (Y/N)?" prompt, which blocks
// shutdown until someone answers it. node.exe is a real executable, not a
// batch file, so this avoids that prompt entirely (matches how
// run-backend.js already spawns uvicorn.exe directly for the same reason).
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const frontendDir = path.join(__dirname, "..", "frontend");
const viteBin = path.join(frontendDir, "node_modules", "vite", "bin", "vite.js");

if (!fs.existsSync(viteBin)) {
  console.error(`Could not find ${viteBin}.\n\nRun "npm install" in frontend/ first.`);
  process.exit(1);
}

const child = spawn(process.execPath, [viteBin], { cwd: frontendDir, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});
