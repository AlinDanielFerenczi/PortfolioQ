// Force-stops this project's dev servers (backend uvicorn + frontend vite).
//
// uvicorn --reload runs a watcher process that respawns a fresh worker
// whenever the current one dies, and on Windows the worker's own command
// line is a generic multiprocessing bootstrap string with no reference to
// uvicorn/this repo at all -- so it can't be found by name or command-line
// matching. The reliable signal is *port ownership*: whatever process is
// actually bound to 8000/5173 right now, plus its immediate parent (to also
// catch the reloader, not just the worker it spawned), tree-killed together.
const { execSync } = require("child_process");

const isWindows = process.platform === "win32";
const PORTS = [8000, 5173];

function psExec(command) {
  return execSync(`powershell -NoProfile -Command "${command}"`, { encoding: "utf8" }).trim();
}

function stopWindows() {
  const pidsToKill = new Set();

  for (const port of PORTS) {
    let owners;
    try {
      owners = psExec(
        `(Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue).OwningProcess`
      );
    } catch {
      continue;
    }
    for (const pid of owners.split(/\s+/).filter(Boolean)) {
      pidsToKill.add(pid);
      try {
        const parentPid = psExec(
          `(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq ${pid} }).ParentProcessId`
        );
        if (parentPid && parentPid !== "0" && parentPid !== "4") {
          pidsToKill.add(parentPid);
        }
      } catch {
        // parent lookup failed -- still kill the port owner itself below
      }
    }
  }

  if (pidsToKill.size === 0) {
    console.log("Nothing to stop.");
    return;
  }

  for (const pid of pidsToKill) {
    try {
      execSync(`taskkill /F /T /PID ${pid}`, { stdio: "ignore" });
      console.log(`Stopped PID ${pid}`);
    } catch {
      // already gone (likely a child killed by an earlier /T in this loop)
    }
  }
}

function stopPosix() {
  for (const port of PORTS) {
    let pids;
    try {
      pids = execSync(`lsof -ti:${port}`, { encoding: "utf8" }).trim();
    } catch {
      continue;
    }
    for (const pid of pids.split("\n").filter(Boolean)) {
      try {
        execSync(`kill -9 ${pid}`, { stdio: "ignore" });
        console.log(`Stopped PID ${pid} on port ${port}`);
      } catch {
        // already gone
      }
    }
  }
}

if (isWindows) stopWindows();
else stopPosix();

console.log("Done.");
