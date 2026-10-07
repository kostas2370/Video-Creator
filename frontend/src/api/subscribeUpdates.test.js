import { subscribeUpdates } from "./subscribeUpdates";

let streams;
let stops;
class MockEventSource {
  constructor(url, options) { this.url = url; this.options = options; this.listeners = {}; this.close = jest.fn(); streams.push(this); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  emit(name) { this.listeners[name]?.({}); }
}
const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
const result = status => ({ ok: true, data: { id: 1, status } });
function subscribe(options) {
  const stop = subscribeUpdates("videos/1/events/", options);
  stops.push(stop);
  return stop;
}
beforeEach(() => { jest.useFakeTimers(); streams = []; stops = []; global.EventSource = MockEventSource; });
afterEach(() => { stops.forEach(stop => stop()); jest.useRealTimers(); delete global.EventSource; });

test("shares a stream and closes it only when the last subscriber leaves", async () => {
  const load = jest.fn().mockResolvedValue(result("GENERATION"));
  const first = subscribe({ load });
  const second = subscribe({ load });
  await flush();
  expect(streams).toHaveLength(1);
  expect(streams[0].options.withCredentials).toBe(true);
  first();
  expect(streams[0].close).not.toHaveBeenCalled();
  second();
  expect(streams[0].close).toHaveBeenCalledTimes(1);
});

test("uses events instead of frequent polling and coalesces bursts", async () => {
  const load = jest.fn().mockResolvedValue(result("GENERATION"));
  const onUpdate = jest.fn();
  subscribe({ load, onUpdate });
  await flush();
  streams[0].emit("ready");
  await flush();
  load.mockClear();
  jest.advanceTimersByTime(4000);
  await flush();
  expect(load).not.toHaveBeenCalled();
  load.mockResolvedValue(result("READY"));
  streams[0].emit("update"); streams[0].emit("update"); streams[0].emit("update");
  jest.advanceTimersByTime(250);
  await flush();
  expect(load).toHaveBeenCalledTimes(1);
  expect(onUpdate).toHaveBeenLastCalledWith({ id: 1, status: "READY" });
});

test("falls back to polling and reloads current state on reconnect", async () => {
  const load = jest.fn().mockResolvedValue(result("RENDERING"));
  subscribe({ load });
  await flush();
  streams[0].emit("ready"); await flush();
  streams[0].onerror(); await flush();
  expect(streams[0].close).toHaveBeenCalled();
  load.mockClear();
  jest.advanceTimersByTime(4000); await flush();
  expect(load).toHaveBeenCalledTimes(1);
  jest.advanceTimersByTime(26000); await flush();
  expect(streams).toHaveLength(2);
  load.mockClear();
  streams[1].emit("ready"); await flush();
  expect(load).toHaveBeenCalledTimes(1);
});

test("ignores results after cancellation", async () => {
  let resolve;
  const onUpdate = jest.fn();
  const stop = subscribe({ load: () => new Promise(done => { resolve = done; }), onUpdate });
  await flush();
  stop(); resolve(result("READY")); await flush();
  expect(onUpdate).not.toHaveBeenCalled();
  expect(jest.getTimerCount()).toBe(0);
});

test("refreshes again when an event arrives during an existing request", async () => {
  let resolve;
  const load = jest.fn().mockImplementationOnce(() => new Promise(done => { resolve = done; }))
    .mockResolvedValue(result("READY"));
  const onUpdate = jest.fn();
  subscribe({ load, onUpdate });
  await flush();
  streams[0].emit("update"); jest.advanceTimersByTime(250);
  resolve(result("GENERATION")); await flush();
  expect(load).toHaveBeenCalledTimes(2);
  expect(onUpdate).toHaveBeenLastCalledWith({ id: 1, status: "READY" });
});

test("polls when EventSource is unavailable", async () => {
  delete global.EventSource;
  const load = jest.fn().mockResolvedValue(result("GENERATION"));
  subscribe({ load }); await flush();
  jest.advanceTimersByTime(4000); await flush();
  expect(load).toHaveBeenCalledTimes(2);
});

test("a new subscriber waits for a fresh request rather than in-flight state", async () => {
  let resolve;
  const load = jest.fn().mockResolvedValueOnce(result("READY"))
    .mockImplementationOnce(() => new Promise(done => { resolve = done; }))
    .mockResolvedValue(result("RENDERING"));
  subscribe({ load }); await flush();
  streams[0].emit("ready");
  await flush();
  const onUpdate = jest.fn();
  subscribe({ load, onUpdate });
  resolve(result("READY")); await flush();
  expect(onUpdate).toHaveBeenCalledTimes(1);
  expect(onUpdate).toHaveBeenLastCalledWith({ id: 1, status: "RENDERING" });
});


test("repeated cleanup cannot remove a newer subscription", async () => {
  const load = jest.fn().mockResolvedValue(result("READY"));
  const oldStop = subscribe({ load }); await flush(); oldStop();
  subscribe({ load }); await flush(); oldStop();
  subscribe({ load }); await flush();
  expect(streams).toHaveLength(2);
  expect(streams[1].close).not.toHaveBeenCalled();
});
