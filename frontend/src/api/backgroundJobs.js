import { toast } from "react-toastify";
import { request } from "./request";

const MAX_AGE = 24 * 60 * 60 * 1000;
const listeners = new Set();
let owner = "", jobs = [], snapshot = [], timer = null;
const waiting = new Map();
const sending = new Map();
const storageKey = id => `viddie:jobs:v1:${encodeURIComponent(id)}`;
const resultOf = job => job.status === "SUCCEEDED"
  ? { ok: true, status: 200, data: job.result }
  : { ok: false, status: null, message: job.error || "Could not finish this job." };
function publish() {
  snapshot = [...jobs];
  if (owner) try {
    jobs.forEach(job => { delete job.storageWarning; });
    localStorage.setItem(storageKey(owner), JSON.stringify(jobs.map(({ polling, ...job }) => job)));
  } catch { jobs.forEach(job => { job.storageWarning = true; }); }
  listeners.forEach(listener => listener());
}
export const subscribeBackgroundJobs = listener => { listeners.add(listener); return () => listeners.delete(listener); };
export const getBackgroundJobs = () => snapshot;
export function configureBackgroundJobs(nextOwner) {
  if (owner === nextOwner) return;
  clearTimeout(timer); timer = null;
  waiting.forEach(resolve => resolve({ ok: false, message: "Account changed. Reopen the project to check its progress." }));
  waiting.clear(); sending.clear();
  owner = nextOwner; jobs = [];
  if (owner) try {
    const saved = JSON.parse(localStorage.getItem(storageKey(owner)) || "[]");
    if (Array.isArray(saved)) jobs = saved.filter(job => job && typeof job.id === "string" && typeof job.pollUrl === "string" && /^draft-jobs\/$|^scenes\/[^/]+\/operation\/$/.test(job.pollUrl) && Number.isFinite(job.createdAt) && Date.now() - job.createdAt < MAX_AGE && ["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"].includes(job.status));
  } catch { /* Start with an empty activity list if browser storage is corrupt. */ }
  jobs.forEach(job => { delete job.polling; if (typeof job.path !== "string" || !/^\/(?!\/)/.test(job.path)) job.path = "/"; });
  publish(); schedule();
}
function schedule() {
  if (timer || !jobs.some(job => ["QUEUED", "RUNNING"].includes(job.status))) return;
  timer = setTimeout(pollBackgroundJobs, 2000);
}
export async function pollBackgroundJobs() {
  clearTimeout(timer); timer = null;
  const account = owner;
  await Promise.all(jobs.filter(job => ["QUEUED", "RUNNING"].includes(job.status)).map(async job => {
    if (job.polling || job.retryAt > Date.now()) return;
    job.polling = true;
    let response;
    try { response = await request({ url: job.pollUrl, params: { job: job.id }, timeout: 15000, notifyError: false }); }
    catch { response = { ok: false }; }
    if (owner !== account || !jobs.includes(job)) return;
    delete job.polling;
    if (Date.now() - job.createdAt >= MAX_AGE) { job.status = "FAILED"; job.error = "This job has expired. Check your project before generating again."; }
    else if (response.ok && ["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"].includes(response.data?.status)) {
      job.status = response.data.status;
      job.result = response.data.result;
      job.error = response.data.error;
      job.reconnecting = false;
      job.failures = 0; job.retryAt = 0;
    } else if ([400, 403, 404].includes(response.status)) { job.status = "FAILED"; job.error = response.message; }
    else { job.reconnecting = true; job.failures = (job.failures || 0) + 1; job.retryAt = Date.now() + Math.min(30000, 2000 * 2 ** Math.min(job.failures, 4)); } // A lost connection never submits another paid request.
    if (["SUCCEEDED", "FAILED"].includes(job.status)) {
      if (job.status === "SUCCEEDED") toast.success(`${job.label} ready. Find the result in Generation activity.`, { toastId: job.id });
      else toast.error(job.error || "Generation failed. Check Generation activity.", { toastId: job.id });
      waiting.get(job.id)?.(resultOf(job)); waiting.delete(job.id);
    }
  }));
  if (owner === account) { publish(); schedule(); }
}
export function dismissBackgroundJob(id) {
  jobs = jobs.filter(job => job.id !== id || !["SUCCEEDED", "FAILED"].includes(job.status)); publish();
}
export function followBackgroundJob(response, { label, pollUrl = "draft-jobs/", key = "" } = {}) {
  if (!response.ok || response.status !== 202 || !response.data?.id) return Promise.resolve(response);
  const existing = jobs.find(job => job.id === response.data.id);
  if (existing && ["SUCCEEDED", "FAILED"].includes(existing.status)) return Promise.resolve(resultOf(existing));
  if (!existing) jobs.push({ id: response.data.id, key, label, pollUrl, status: "QUEUED", createdAt: Date.now(), path: window.location.pathname });
  const promise = new Promise(resolve => {
    const previous = waiting.get(response.data.id);
    waiting.set(response.data.id, result => { previous?.(result); resolve(result); });
  });
  publish(); schedule();
  return promise;
}
export function runBackgroundDraft(url, data, label, method = "post") {
  const key = JSON.stringify([method, url, data]);
  if (sending.has(key)) return sending.get(key);
  const active = jobs.find(job => job.key === key && ["QUEUED", "RUNNING"].includes(job.status));
  if (active) return followBackgroundJob({ ok: true, status: 202, data: { id: active.id } }, { label, key });
  const account = owner;
  const promise = request({ method, url, data, headers: { Prefer: "respond-async" }, notifyError: false }).then(response => {
    if (owner !== account) return { ok: false, message: "Account changed. Reopen the project to check its progress." };
    if (!response.ok) toast.error(response.message || "Could not queue the draft. Please try again.");
    return followBackgroundJob(response, { label, key });
  }).finally(() => { if (owner === account) sending.delete(key); });
  sending.set(key, promise);
  return promise;
}
