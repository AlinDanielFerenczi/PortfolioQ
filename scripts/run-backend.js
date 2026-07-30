const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const isWindows = process.platform === "win32";
const uvicornPath = path.join(
  __dirname,
  "..",
  "venv",
  isWindows ? "Scripts" : "bin",
  isWindows ? "uvicorn.exe" : "uvicorn"
);

if (!fs.existsSync(uvicornPath)) {
  const pipHint = isWindows ? "venv\\Scripts\\pip" : "venv/bin/pip";
  console.error(
    `Could not find ${uvicornPath}.\n\n` +
      "Set up the Python venv first (from the repo root):\n" +
      "  python3 -m venv venv\n" +
      `  ${pipHint} install -r requirements.txt\n`
  );
  process.exit(1);
}

const child = spawn(uvicornPath, ["main:app", "--reload"], { stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});
