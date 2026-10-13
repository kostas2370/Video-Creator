import { describe, expect, it, vi } from "vitest";
import { waitForSceneOperation } from "./sceneOperation";

describe("background scene operations", () => {
  it("follows queued and running work to its final result", async () => {
    const load = vi.fn()
      .mockResolvedValueOnce({ ok: true, data: { status: "QUEUED" } })
      .mockResolvedValueOnce({ ok: true, data: { status: "RUNNING" } })
      .mockResolvedValueOnce({ ok: true, data: { status: "SUCCEEDED", result: { text: "Updated" } } });
    const pause = vi.fn();
    expect(await waitForSceneOperation(load, { pause })).toMatchObject({ ok: true, data: { text: "Updated" } });
    expect(pause).toHaveBeenCalledTimes(2);
  });
  it("reports failed jobs instead of a successful save", async () => {
    expect(await waitForSceneOperation(async () => ({ ok: true, data: { status: "FAILED", error: "Try again" } })))
      .toMatchObject({ ok: false, data: null, message: "Try again" });
  });
  it("stops on authentication or network failures", async () => {
    const load = vi.fn().mockResolvedValue({ ok: false, status: 401, message: "Sign in" });
    expect(await waitForSceneOperation(load)).toMatchObject({ ok: false, status: 401 });
    expect(load).toHaveBeenCalledTimes(1);
  });
  it("bounds polling without reporting completion", async () => {
    const load = vi.fn().mockResolvedValue({ ok: true, data: { status: "RUNNING" } });
    expect(await waitForSceneOperation(load, { pause: vi.fn(), maxAttempts: 2 })).toMatchObject({ ok: false });
    expect(load).toHaveBeenCalledTimes(2);
  });
});
