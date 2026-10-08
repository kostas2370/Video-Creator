import { waitForVideo } from "./waitForVideo";
import { subscribeUpdates } from "./subscribeUpdates";

jest.mock("./subscribeUpdates", () => ({ subscribeUpdates: jest.fn() }));
jest.mock("./apiService", () => ({ getVideo: jest.fn() }));
let listener;
let stop;
beforeEach(() => {
  jest.useFakeTimers(); stop = jest.fn();
  subscribeUpdates.mockImplementation((path, options) => { listener = options; return stop; });
});
afterEach(() => jest.useRealTimers());

test("resolves on completion and unsubscribes", async () => {
  const watcher = waitForVideo(7);
  listener.onUpdate({ id: 7, status: "RENDERING" });
  listener.onUpdate({ id: 7, status: "COMPLETED" });
  expect(await watcher.promise).toEqual({ outcome: "SETTLED", video: { id: 7, status: "COMPLETED" } });
  expect(stop).toHaveBeenCalledTimes(1);
  expect(jest.getTimerCount()).toBe(0);
});
test("cancellation resolves without a completion notification", async () => {
  const watcher = waitForVideo(7); watcher.cancel();
  expect(await watcher.promise).toEqual({ outcome: "CANCELLED", video: null });
  expect(stop).toHaveBeenCalledTimes(1);
});
test("bounds failures and operation duration", async () => {
  const failed = waitForVideo(7, { maxConsecutiveErrors: 2 });
  listener.onError(); listener.onError();
  expect((await failed.promise).outcome).toBe("UNREACHABLE");
  const timed = waitForVideo(7, { timeoutMs: 1000 });
  jest.advanceTimersByTime(1000);
  expect((await timed.promise).outcome).toBe("TIMEOUT");
});
