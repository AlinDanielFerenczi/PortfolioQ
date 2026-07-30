const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // no JSON body (e.g. network-level failure) -- fall through to status check
  }

  if (!res.ok) {
    const detail = data && data.detail ? data.detail : `Request failed with status ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

export const runClassical = (req) => request("/optimize/classical", { method: "POST", body: req });
export const runQaoa = (req) => request("/optimize/qaoa", { method: "POST", body: req });
export const runQaoaXy = (req) => request("/optimize/qaoa-xy", { method: "POST", body: req });
export const runCompareAll = (req) => request("/optimize/compare-all", { method: "POST", body: req });

export const submitQaoa = (req) => request("/optimize/qaoa/submit", { method: "POST", body: req });
export const submitQaoaXy = (req) => request("/optimize/qaoa-xy/submit", { method: "POST", body: req });
export const submitCompareAll = (req) =>
  request("/optimize/compare-all/submit", { method: "POST", body: req });

export const getJobStatus = (jobId) => request(`/jobs/${jobId}`);

export const METHODS = {
  classical: { label: "Classical", run: (req) => request("/optimize/classical", { method: "POST", body: req }) },
  qaoa: { label: "QAOA (penalty)", run: runQaoa, submit: submitQaoa },
  "qaoa-xy": { label: "QAOA (XY-mixer)", run: runQaoaXy, submit: submitQaoaXy },
  "compare-all": { label: "Compare All", run: runCompareAll, submit: submitCompareAll },
};

// Maps the `method` string a job reports (jobs.py / main.py's submit_job calls)
// back to the frontend's method key, so a resumed job renders correctly even
// if the form's current method selection has since changed.
export const BACKEND_METHOD_KEYS = {
  qaoa: "qaoa",
  qaoa_xy_mixer: "qaoa-xy",
  compare_all: "compare-all",
};
