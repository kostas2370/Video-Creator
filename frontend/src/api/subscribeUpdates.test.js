import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("./apiService", () => ({ refreshToken: vi.fn().mockResolvedValue({ ok: true }) }));
import { subscribeUpdates } from "./subscribeUpdates";
import { refreshToken } from "./apiService";
let sources, unsubscribe;

beforeEach(() => {
  vi.useFakeTimers(); sources = [];
  const page = new EventTarget(); page.visibilityState = "visible"; vi.stubGlobal("document", page);
  refreshToken.mockResolvedValue({ ok: true });
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

function setVisibility(state) {
  document.visibilityState = state;
  document.dispatchEvent(new Event("visibilitychange"));
}

it("releases background streams and reconciles when the tab becomes visible", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  unsubscribe = subscribeUpdates("videos/background/events/", { load });
  await vi.advanceTimersByTimeAsync(0);
  const first = sources[0];
  setVisibility("hidden");
  expect(first.close).toHaveBeenCalledOnce();
  const baseline = load.mock.calls.length;
  first.emit("update"); first.emit("stream-open"); first.emit("stream-reset"); first.onerror();
  await vi.advanceTimersByTimeAsync(90000);
  expect(sources).toHaveLength(1);
  expect(load).toHaveBeenCalledTimes(baseline);
  expect(refreshToken).not.toHaveBeenCalled();
  setVisibility("visible");
  await vi.advanceTimersByTimeAsync(0);
  expect(sources).toHaveLength(2);
  expect(load).toHaveBeenCalledTimes(baseline + 1);
});

it("does not open streams or fetch resource data in a hidden tab", async () => {
  setVisibility("hidden");
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  unsubscribe = subscribeUpdates("videos/hidden/events/", { load });
  await vi.advanceTimersByTimeAsync(60000);
  expect(sources).toHaveLength(0);
  expect(load).not.toHaveBeenCalled();
  setVisibility("visible");
  await vi.advanceTimersByTimeAsync(0);
  expect(sources).toHaveLength(1);
  expect(load).toHaveBeenCalledOnce();
});

it("stops retrying after authentication is refused", async () => {
  const onError = vi.fn();
  refreshToken.mockResolvedValueOnce({ ok: false, status: 403 });
  unsubscribe = subscribeUpdates("videos/signed-out/events/", { load: vi.fn().mockResolvedValue({ ok: true, data: {} }), onError });
  await vi.advanceTimersByTimeAsync(0);
  sources[0].onerror();
  await vi.advanceTimersByTimeAsync(120000);
  expect(refreshToken).toHaveBeenCalledOnce();
  expect(sources).toHaveLength(1);
  expect(onError).toHaveBeenCalledWith({ ok: false, status: 403 });
  setVisibility("hidden"); setVisibility("visible");
  expect(sources).toHaveLength(1);
});

it("shares pending authentication between streams and does not reopen after hiding", async () => {
  let resolveRefresh;
  refreshToken.mockImplementationOnce(() => new Promise(resolve => { resolveRefresh = resolve; }));
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  const first = subscribeUpdates("videos/one/events/", { load });
  const second = subscribeUpdates("notifications/two/events/", { load });
  unsubscribe = () => { first(); second(); };
  await vi.advanceTimersByTimeAsync(0);
  sources[0].onerror(); sources[1].onerror();
  await vi.advanceTimersByTimeAsync(30000);
  expect(refreshToken).toHaveBeenCalledOnce();
  setVisibility("hidden");
  resolveRefresh({ ok: true });
  await vi.advanceTimersByTimeAsync(0);
  expect(sources).toHaveLength(2);
  setVisibility("visible");
  expect(sources).toHaveLength(4);
});

it("cleans up visibility listeners and retries when the last subscriber leaves", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  unsubscribe = subscribeUpdates("videos/cleanup/events/", { load });
  await vi.advanceTimersByTimeAsync(0);
  sources[0].onerror();
  unsubscribe();
  setVisibility("hidden"); setVisibility("visible");
  await vi.advanceTimersByTimeAsync(60000);
  expect(refreshToken).not.toHaveBeenCalled();
  expect(sources).toHaveLength(1);
});


it("can resume when a tab hides before its initial refresh starts", async () => {
  const load = vi.fn().mockResolvedValue({ ok: true, data: {} });
  unsubscribe = subscribeUpdates("videos/hide-race/events/", { load });
  setVisibility("hidden");
  await vi.advanceTimersByTimeAsync(0);
  expect(load).not.toHaveBeenCalled();
  setVisibility("visible");
  await vi.advanceTimersByTimeAsync(0);
  expect(load).toHaveBeenCalledOnce();
});
