import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { subscribeUpdates } from "./subscribeUpdates";
let cleanup;
const tick = (ms = 0) => vi.advanceTimersByTimeAsync(ms);
function visible(state) { document.visibilityState = state; document.dispatchEvent(new Event("visibilitychange")); }
beforeEach(() => {
  vi.useFakeTimers(); cleanup = [];
  const page = new EventTarget(); page.visibilityState = "visible"; vi.stubGlobal("document", page);
  vi.stubGlobal("EventSource", vi.fn());
});
afterEach(async () => { cleanup.forEach(stop => stop()); await tick(); vi.useRealTimers(); vi.unstubAllGlobals(); });
function watch(path, options) { const stop = subscribeUpdates(path, options); cleanup.push(stop); return stop; }

it("uses short requests without persistent streams and slows polling after work finishes", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: { status: "GENERATION" } });
  const onUpdate = vi.fn();
  watch("videos/one/events/", { load, onUpdate });
  await tick();
  expect(EventSource).not.toHaveBeenCalled();
  expect(load).toHaveBeenCalledOnce();
  await tick(3000);
  expect(load).toHaveBeenCalledTimes(2);
  expect(onUpdate).toHaveBeenCalledOnce(); // Identical data does not rerender the editor.
  load.mockResolvedValue({ ok: true, data: { status: "READY" } });
  await tick(3000);
  expect(onUpdate).toHaveBeenLastCalledWith({ status: "READY" });
  await tick(14000);
  expect(load).toHaveBeenCalledTimes(3);
  await tick(1000);
  expect(load).toHaveBeenCalledTimes(4);
});

it("leaves connections free even when twelve progress cards subscribe at once", async () => {
  let active = 0, peak = 0;
  const releases = [];
  const load = vi.fn(() => new Promise(resolve => { active++; peak = Math.max(peak, active); releases.push(() => { active--; resolve({ ok: true, data: { status: "GENERATION" } }); }); }));
  for (let i = 0; i < 12; i++) watch(`videos/${i}/events/`, { load });
  await tick();
  expect(load).toHaveBeenCalledTimes(2);
  for (let i = 0; i < 12; i++) { releases[i](); await tick(); }
  expect(load).toHaveBeenCalledTimes(12);
  expect(peak).toBe(2);
  expect(EventSource).not.toHaveBeenCalled();
});

it("shares one resource refresh while giving a new subscriber a response started after subscription", async () => {
  let finish;
  const load = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValue({ ok: true, data: { status: "GENERATION" } });
  const first = vi.fn(), second = vi.fn();
  watch("videos/shared/events/", { load, onUpdate: first });
  await tick();
  watch("videos/shared/events/", { load, onUpdate: second });
  finish({ ok: true, data: { status: "READY" } });
  await tick();
  expect(first).toHaveBeenCalledWith({ status: "READY" });
  expect(second).not.toHaveBeenCalledWith({ status: "READY" });
  expect(second).toHaveBeenCalledWith({ status: "GENERATION" });
  expect(load).toHaveBeenCalledTimes(2);
});

it("aborts outstanding requests when hidden and reconciles immediately on return", async () => {
  let signal;
  const load = vi.fn().mockImplementationOnce(options => { signal = options.signal; return new Promise(() => {}); }).mockResolvedValue({ ok: true, data: {} });
  watch("videos/background/events/", { load });
  await tick();
  visible("hidden");
  expect(signal.aborted).toBe(true);
  await tick(60000);
  expect(load).toHaveBeenCalledOnce();
  visible("visible");
  await tick();
  expect(load).toHaveBeenCalledTimes(2);
});

it("does not request data when hidden, including a hide before the first microtask", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  watch("videos/hidden/events/", { load });
  visible("hidden");
  await tick(60000);
  expect(load).not.toHaveBeenCalled();
  visible("visible");
  await tick();
  expect(load).toHaveBeenCalledOnce();
});

it("releases queued and running requests when subscriptions are removed", async () => {
  const signals = [];
  const load = vi.fn(options => { signals.push(options.signal); return new Promise(() => {}); });
  const stops = [0, 1, 2].map(i => watch(`videos/cleanup-${i}/events/`, { load }));
  await tick();
  stops.forEach(stop => stop());
  await tick(60000);
  expect(signals.every(signal => signal.aborted)).toBe(true);
  expect(load).toHaveBeenCalledTimes(2);
});

it("times out a stuck update so other projects can continue loading", async () => {
  const onError = vi.fn();
  const stuck = vi.fn().mockReturnValue(new Promise(() => {}));
  const ready = vi.fn().mockResolvedValue({ ok: true, data: {} });
  watch("videos/stuck-a/events/", { load: stuck, onError });
  watch("videos/stuck-b/events/", { load: stuck, onError });
  watch("videos/ready/events/", { load: ready });
  await tick(15000);
  expect(ready).toHaveBeenCalledOnce();
  expect(onError).toHaveBeenCalledTimes(2);
  expect(stuck.mock.calls[0][0].signal.aborted).toBe(true);
});

it("stops fetching when authentication or access is refused", async () => {
  const onError = vi.fn();
  const load = vi.fn().mockResolvedValue({ ok: false, status: 403 });
  watch("videos/denied/events/", { load, onError });
  await tick(120000);
  visible("hidden"); visible("visible");
  await tick();
  expect(load).toHaveBeenCalledOnce();
  expect(onError).toHaveBeenCalledWith({ ok: false, status: 403 });
});

it("refreshes notifications less often and reports recovery even if data is unchanged", async () => {
  const onUpdate = vi.fn();
  const load = vi.fn().mockResolvedValueOnce({ ok: true, data: { unread: 0 } }).mockResolvedValueOnce({ ok: false }).mockResolvedValue({ ok: true, data: { unread: 0 } });
  watch("notifications/events/", { load, onUpdate });
  await tick(29999);
  expect(load).toHaveBeenCalledOnce();
  await tick(30001);
  expect(onUpdate).toHaveBeenCalledTimes(2);
});

it("keeps a replacement subscription alive if an old cleanup is called twice", async () => {
  const old = watch("videos/replaced/events/", { load: vi.fn().mockResolvedValue({ ok: true, data: {} }) });
  await tick();
  old();
  const load = vi.fn().mockResolvedValue({ ok: true, data: { status: "GENERATION" } });
  watch("videos/replaced/events/", { load });
  old();
  await tick();
  visible("hidden"); visible("visible");
  await tick();
  expect(load).toHaveBeenCalledTimes(2);
});
