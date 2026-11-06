import { afterEach, expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { followBackgroundJob, runBackgroundDraft } from "./backgroundJobs";
afterEach(() => vi.resetAllMocks());
it("follows a queued task until its result is ready", async () => {
  request.mockResolvedValueOnce({ ok: true, data: { status: "RUNNING" } }).mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { text: "A draft" } } });
  const pause = vi.fn();
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } }, { pause })).toMatchObject({ ok: true, data: { text: "A draft" } });
  expect(pause).toHaveBeenCalledTimes(1);
  expect(request.mock.calls[0][0]).toMatchObject({ url: "draft-jobs/", params: { job: "task" } });
});
it("returns task failures and connection errors without submitting another task", async () => {
  request.mockResolvedValueOnce({ ok: true, data: { status: "FAILED", error: "Please retry" } });
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } })).toMatchObject({ ok: false, message: "Please retry" });
  request.mockResolvedValueOnce({ ok: false, status: 401 });
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } })).toMatchObject({ ok: false, status: 401 });
  expect(request.mock.calls.every(([args]) => !args.method)).toBe(true);
});
it("returns immediate scene saves and bounds the polling wait", async () => {
  const saved = { ok: true, status: 200, data: { text: "Saved" } };
  expect(await followBackgroundJob(saved)).toBe(saved);
  request.mockResolvedValue({ ok: true, data: { status: "QUEUED" } });
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } }, { pause: vi.fn(), maxAttempts: 2 })).toMatchObject({ ok: false });
});
it("queues the requested Celery operation and reads its result", async () => {
  request.mockResolvedValueOnce({ ok: true, status: 202, data: { id: "task" } }).mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { story: "A story" } } });
  expect(await runBackgroundDraft("videos/draft_story/", { prompt: "Mystery" })).toMatchObject({ ok: true, data: { story: "A story" } });
  expect(request.mock.calls[0][0]).toEqual({ method: "post", url: "videos/draft_story/", data: { prompt: "Mystery" }, notifyError: false });
});

it.each([null, 408, 429, 503])("retries temporary status failures (%s) using the same task", async (status) => {
  request.mockResolvedValueOnce({ ok: false, status }).mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: "Done" } });
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "same-task" } }, { pause: vi.fn() })).toMatchObject({ ok: true, data: "Done" });
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls.every(([args]) => !args.method && args.params.job === "same-task")).toBe(true);
});
it("bounds consecutive status failures and stops on nonretryable errors", async () => {
  request.mockResolvedValue({ ok: false, status: 503 });
  const pause = vi.fn();
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } }, { pause })).toMatchObject({ ok: false, status: 503 });
  expect(request).toHaveBeenCalledTimes(4);
  expect(pause).toHaveBeenCalledTimes(3);
  request.mockClear().mockResolvedValue({ ok: false, status: 404 });
  await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } }, { pause });
  expect(request).toHaveBeenCalledTimes(1);
});
it("does not retry failed task submissions", async () => {
  request.mockResolvedValue({ ok: false, status: 503 });
  expect(await runBackgroundDraft("videos/draft_story/", {})).toMatchObject({ ok: false, status: 503 });
  expect(request).toHaveBeenCalledTimes(1);
});

it("resets temporary failure count after a successful status check", async () => {
  request.mockResolvedValueOnce({ ok: false, status: 503 }).mockResolvedValueOnce({ ok: true, data: { status: "RUNNING" } });
  for (let i = 0; i < 3; i += 1) request.mockResolvedValueOnce({ ok: false, status: null });
  request.mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: "Done" } });
  expect(await followBackgroundJob({ ok: true, status: 202, data: { id: "task" } }, { pause: vi.fn() })).toMatchObject({ ok: true, data: "Done" });
});
