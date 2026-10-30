import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("./apiService", () => ({ refreshToken: vi.fn().mockResolvedValue({ ok: true }) }));
import { subscribeUpdates } from "./subscribeUpdates";
import { refreshToken } from "./apiService";
let sources, unsubscribe;

beforeEach(() => {
  vi.useFakeTimers(); sources = [];
  vi.stubGlobal("EventSource", class {
    listeners = new Map(); close = vi.fn();
    constructor(url) { this.url = url; sources.push(this); }
    addEventListener(name, callback) { this.listeners.set(name, callback); }
    emit(name) { this.listeners.get(name)?.(); }
  });
});
afterEach(() => { unsubscribe?.(); unsubscribe = null; vi.useRealTimers(); vi.unstubAllGlobals(); vi.clearAllMocks(); });

it("refreshes on server events rather than repeatedly polling project data", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: { status: "READY" } });
  const onUpdate = vi.fn();
  unsubscribe = subscribeUpdates("clips/project/events/", { load, onUpdate });
  await vi.advanceTimersByTimeAsync(0);
  const baseline = load.mock.calls.length;
  await vi.advanceTimersByTimeAsync(15000);
  expect(load).toHaveBeenCalledTimes(baseline);
  sources[0].emit("update"); sources[0].emit("update");
  await vi.advanceTimersByTimeAsync(250);
  expect(load).toHaveBeenCalledTimes(baseline + 1);
  expect(onUpdate).toHaveBeenLastCalledWith({ status: "READY" });
});

it("renews authentication on reconnect and reconciles missed events when the stream opens", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  unsubscribe = subscribeUpdates("clips/reconnect/events/", { load });
  await vi.advanceTimersByTimeAsync(0);
  sources[0].onerror();
  await vi.advanceTimersByTimeAsync(30000);
  expect(refreshToken).toHaveBeenCalledTimes(1);
  expect(sources).toHaveLength(2);
  const baseline = load.mock.calls.length;
  sources[1].emit("stream-open");
  await vi.advanceTimersByTimeAsync(0);
  expect(load).toHaveBeenCalledTimes(baseline + 1);
});
