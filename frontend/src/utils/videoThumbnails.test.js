import { describe, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ ensureVideoThumbnail: vi.fn() }));
import { ensureVideoThumbnail } from "../api/apiService";
import { loadVideoThumbnail } from "./videoThumbnails";

describe("saved library thumbnails", () => {
  it("shares an in-flight request and reuses its saved image", async () => {
    const video = { id: "shared", updated_at: "original", output: "export.mp4" };
    const result = { ok: true, data: { thumbnail: "saved.jpg" } };
    ensureVideoThumbnail.mockResolvedValueOnce(result);
    const first = loadVideoThumbnail(video);
    expect(loadVideoThumbnail(video)).toBe(first);
    expect(await first).toEqual(result);
    expect(await loadVideoThumbnail(video)).toEqual(result);
    expect(ensureVideoThumbnail).toHaveBeenCalledTimes(1);
  });
  it("requests a new image for a new export version", async () => {
    ensureVideoThumbnail.mockClear();
    ensureVideoThumbnail.mockResolvedValue({ ok: true, data: { thumbnail: "saved.jpg" } });
    await loadVideoThumbnail({ id: "changed", updated_at: "old", output: "export.mp4" });
    await loadVideoThumbnail({ id: "changed", updated_at: "new", output: "export.mp4" });
    expect(ensureVideoThumbnail).toHaveBeenCalledTimes(2);
  });
  it("allows a failed request to be retried on a later visit", async () => {
    const video = { id: "retry" };
    ensureVideoThumbnail.mockResolvedValueOnce({ ok: false });
    expect((await loadVideoThumbnail(video)).ok).toBe(false);
    ensureVideoThumbnail.mockResolvedValueOnce({ ok: true, data: { thumbnail: "recovered.jpg" } });
    expect((await loadVideoThumbnail(video)).data.thumbnail).toBe("recovered.jpg");
  });
});
