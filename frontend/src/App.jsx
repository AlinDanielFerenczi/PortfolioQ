import { useEffect, useMemo, useState } from "react";
import "./App.css";
import RequestForm from "./components/RequestForm";
import RunModeToggle from "./components/RunModeToggle";
import JobStatusBanner from "./components/JobStatusBanner";
import ErrorBanner from "./components/ErrorBanner";
import ResultSummaryCard from "./components/ResultSummaryCard";
import ComparisonCharts from "./components/ComparisonCharts";
import ConclusionPanel from "./components/ConclusionPanel";
import { METHODS, BACKEND_METHOD_KEYS } from "./api";
import { buildRequestBody, validateForm } from "./validation";
import { useJobPolling } from "./hooks/useJobPolling";

const DEFAULT_FORM = {
  tickersRaw: "AAPL, MSFT, GOOGL, AMZN, NVDA",
  budget: 2,
  risk_factor: 0.5,
  reps: 1,
  shots: 1024,
  maxiter: 100,
  backend: "aer_simulator",
  mixer_topology: "ring",
  lookback_days: 30,
  method: "compare-all",
};

const JOB_STORAGE_KEY = "qaoa-portfolio:lastJobId";

function repsFromResult(method, result) {
  if (!result) return undefined;
  const metadata = method === "compare-all" ? result.qaoa_penalty.metadata : result.metadata;
  return metadata ? metadata.reps : undefined;
}

function ResultDisplay({ method, result, reps }) {
  if (!result) return null;
  if (method === "compare-all") {
    return (
      <>
        <ComparisonCharts compare={result} />
        <ConclusionPanel compare={result} reps={reps} />
        <div className="result-cards-row">
          <ResultSummaryCard result={result.classical} />
          <ResultSummaryCard result={result.qaoa_penalty} />
          <ResultSummaryCard result={result.qaoa_xy_mixer} />
        </div>
      </>
    );
  }
  return <ResultSummaryCard result={result} />;
}

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [runModeOverride, setRunModeOverride] = useState(null);
  const [loading, setLoading] = useState(false);
  const [blockingResult, setBlockingResult] = useState(null);
  const [blockingError, setBlockingError] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [resumed, setResumed] = useState(false);

  const { job, pollError } = useJobPolling(jobId);

  const { errors } = useMemo(() => validateForm(form), [form]);

  // Jobs run in the backend's in-memory store and survive independently of
  // this page -- so if the tab reloads/crashes mid-run, resume polling
  // whatever job was last in flight instead of losing track of it.
  useEffect(() => {
    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY);
    if (savedJobId) {
      setJobId(savedJobId);
      setResumed(true);
    }
  }, []);

  useEffect(() => {
    if (pollError) localStorage.removeItem(JOB_STORAGE_KEY);
  }, [pollError]);

  const isClassical = form.method === "classical";
  const backendIsSimulator = !form.backend.trim() || form.backend.trim() === "aer_simulator";
  const effectiveRunMode = isClassical
    ? "blocking"
    : runModeOverride ?? (backendIsSimulator ? "blocking" : "async");

  const asyncBusy = Boolean(jobId) && (!job || (job.status !== "completed" && job.status !== "failed"));
  const busy = loading || asyncBusy;

  const updateForm = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const dismissJob = () => {
    localStorage.removeItem(JOB_STORAGE_KEY);
    setJobId(null);
    setResumed(false);
  };

  const handleRun = async () => {
    const { errors: currentErrors } = validateForm(form);
    if (currentErrors.length > 0) return;

    setBlockingResult(null);
    setBlockingError(null);
    setJobId(null);
    setResumed(false);
    localStorage.removeItem(JOB_STORAGE_KEY);

    const body = buildRequestBody(form);
    const methodDef = METHODS[form.method];

    if (effectiveRunMode === "blocking") {
      setLoading(true);
      try {
        const result = await methodDef.run(body);
        setBlockingResult(result);
      } catch (err) {
        setBlockingError(err.message);
      } finally {
        setLoading(false);
      }
    } else {
      try {
        const submitted = await methodDef.submit(body);
        setJobId(submitted.job_id);
        localStorage.setItem(JOB_STORAGE_KEY, submitted.job_id);
      } catch (err) {
        setBlockingError(err.message);
      }
    }
  };

  const asyncFailed = job && job.status === "failed";
  const asyncResult = job && job.status === "completed" ? job.result : null;
  const displayMethod = job && asyncResult ? BACKEND_METHOD_KEYS[job.method] || form.method : form.method;
  const displayResult = blockingResult || asyncResult;
  const displayReps = blockingResult ? form.reps : repsFromResult(displayMethod, asyncResult);

  return (
    <div className="page">
      <header className="page-header">
        <h1>QAOA Portfolio Optimization</h1>
        <p>Build a request, run it against the simulator or real IBM hardware, and compare results.</p>
      </header>

      <section className="panel">
        <RequestForm form={form} onChange={updateForm} disabled={busy} />
        <RunModeToggle
          mode={effectiveRunMode}
          onChange={setRunModeOverride}
          disabled={isClassical || busy}
        />
        <button className="run-button" onClick={handleRun} disabled={errors.length > 0 || busy}>
          {busy ? "Running…" : `Run ${METHODS[form.method].label}`}
        </button>
      </section>

      <section className="panel">
        {loading && (
          <div className="banner banner-info">
            <span className="spinner" aria-hidden="true" />
            Running {METHODS[form.method].label} on {form.backend || "aer_simulator"}…
          </div>
        )}
        <ErrorBanner message={blockingError} />
        <ErrorBanner message={pollError} />
        {resumed && jobId && (
          <div className="banner banner-info resumed-banner">
            <span>Resumed a job from a previous session — it kept running on the backend while this page was away.</span>
            <button type="button" className="dismiss-button" onClick={dismissJob}>
              Dismiss
            </button>
          </div>
        )}
        {jobId && <JobStatusBanner job={job} />}
        {asyncFailed && <ErrorBanner message={job.error} />}

        <ResultDisplay method={displayMethod} result={displayResult} reps={displayReps} />
      </section>
    </div>
  );
}
