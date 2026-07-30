import { useEffect, useState } from "react";

const STATUS_LABELS = {
  pending: "Pending — waiting for a worker",
  running: "Running — waiting on the backend (may be queued on real hardware)",
  completed: "Completed",
  failed: "Failed",
};

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

export default function JobStatusBanner({ job }) {
  const [now, setNow] = useState(Date.now());
  const isTerminal = job && (job.status === "completed" || job.status === "failed");

  useEffect(() => {
    if (isTerminal) return undefined;
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [isTerminal]);

  if (!job) return null;

  const elapsedMs = job.submitted_at
    ? now - new Date(job.submitted_at).getTime()
    : 0;

  return (
    <div className={`banner job-status job-status-${job.status}`}>
      <div className="job-status-row">
        {!isTerminal && <span className="spinner" aria-hidden="true" />}
        <span className="job-status-label">{STATUS_LABELS[job.status] || job.status}</span>
        <span className="job-status-elapsed">{formatElapsed(elapsedMs)} elapsed</span>
      </div>
      {!isTerminal && (
        <div className="progress-bar" aria-hidden="true">
          <div className="progress-bar-fill" />
        </div>
      )}
      <div className="job-status-meta">
        job {job.job_id} &middot; method: {job.method}
      </div>
    </div>
  );
}
