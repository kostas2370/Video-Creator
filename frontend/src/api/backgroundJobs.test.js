// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { configureBackgroundJobs, dismissBackgroundJob, followBackgroundJob, getBackgroundJobs, pollBackgroundJobs, runBackgroundDraft } from "./backgroundJobs";

beforeEach(() => { vi.useFakeTimers(); localStorage.clear(); configureBackgroundJobs(""); configureBackgroundJobs("owner-a"); vi.clearAllMocks(); });
afterEach(() => { configureBackgroundJobs(""); vi.useRealTimers(); });
it("queues once, follows progress and returns a reviewable result", async () => {
  request.mockResolvedValueOnce({ ok: true, status: 202, data: { id: "signed-job" } });
  const first = runBackgroundDraft("videos/draft_story/", { prompt: "Mystery" }, "Story draft");
  const second = runBackgroundDraft("videos/draft_story/", { prompt: "Mystery" }, "Story draft");
  expect(second).toBe(first);
  await Promise.resolve();
  expect(request).toHaveBeenCalledTimes(1);
  expect(request).toHaveBeenCalledWith(expect.objectContaining({ method: "post", url: "videos/draft_story/" }));
  expect(getBackgroundJobs()[0]).toMatchObject({ label: "Story draft", status: "QUEUED" });
  request.mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { story: "A new story" } } });
  await pollBackgroundJobs();
  expect(await first).toMatchObject({ ok: true, data: { story: "A new story" } });
  expect(getBackgroundJobs()[0].status).toBe("SUCCEEDED");
  dismissBackgroundJob("signed-job");
  expect(getBackgroundJobs()).toEqual([]);
});
it("recovers queued jobs after reload or navigation without submitting again", async () => {
  localStorage.setItem("viddie:jobs:v1:owner-b", JSON.stringify([{ id: "recovered", label: "Cast draft", pollUrl: "draft-jobs/", status: "RUNNING", createdAt: Date.now(), path: "/series/" }]));
  configureBackgroundJobs("owner-b");
  request.mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { cast: [{ name: "Milo" }] } } });
  await pollBackgroundJobs();
  expect(request).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toMatchObject({ url: "draft-jobs/", params: { job: "recovered" } });
  expect(getBackgroundJobs()[0].result.cast[0].name).toBe("Milo");
});
it("keeps polling after a lost connection and never duplicates the paid request", async () => {
  const pending = followBackgroundJob({ ok: true, status: 202, data: { id: "scene-job" } }, { label: "Scene visual", pollUrl: "scenes/scene-id/operation/" });
  request.mockResolvedValueOnce({ ok: false, status: null });
  await pollBackgroundJobs();
  expect(getBackgroundJobs()[0]).toMatchObject({ status: "QUEUED", reconnecting: true });
  vi.setSystemTime(Date.now() + 4000);
  request.mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { text: "Saved" } } });
  await pollBackgroundJobs();
  expect(await pending).toMatchObject({ ok: true, data: { text: "Saved" } });
  expect(request.mock.calls.every(([args]) => !args.method || args.method === "get")).toBe(true);
});
it("isolates accounts and prevents a late poll from showing another account's result", async () => {
  const pending = followBackgroundJob({ ok: true, status: 202, data: { id: "private" } }, { label: "Private story" });
  let finish;
  request.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  const poll = pollBackgroundJobs();
  configureBackgroundJobs("owner-b");
  expect(await pending).toMatchObject({ ok: false });
  finish({ ok: true, data: { status: "SUCCEEDED", result: { story: "Private" } } });
  await poll;
  expect(getBackgroundJobs()).toEqual([]);
  expect(localStorage.getItem("viddie:jobs:v1:owner-b")).not.toContain("Private");
});
it("reports expired or failed jobs without overwriting drafts", async () => {
  const pending = followBackgroundJob({ ok: true, status: 202, data: { id: "failed" } }, { label: "Memory draft" });
  request.mockResolvedValueOnce({ ok: true, data: { status: "FAILED", error: "The script changed" } });
  await pollBackgroundJobs();
  expect(await pending).toMatchObject({ ok: false, message: "The script changed" });
  expect(getBackgroundJobs()[0].status).toBe("FAILED");
});
