import { useEffect, useRef, useState } from "react";
import { getJobStatus } from "../api";

const POLL_INTERVAL_MS = 2000;
const TERMINAL_STATUSES = new Set(["completed", "failed"]);

export function useJobPolling(jobId) {
  const [job, setJob] = useState(null);
  const [pollError, setPollError] = useState(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    setJob(null);
    setPollError(null);
    if (!jobId) return undefined;

    let cancelled = false;

    const poll = async () => {
      try {
        const data = await getJobStatus(jobId);
        if (cancelled) return;
        setJob(data);
        if (!TERMINAL_STATUSES.has(data.status)) {
          timeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setPollError(err.message);
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [jobId]);

  return { job, pollError };
}
