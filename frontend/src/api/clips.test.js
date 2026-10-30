import { beforeEach, expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { createClip, saveClip, exportClips, downloadClip, retryClipProject } from "./apiService";

beforeEach(() => vi.clearAllMocks());
it("routes clip edits and exports through their owning project", () => {
  createClip("p", { start: 10, end: 40 });
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "clips/p/clips/", data: { start: 10, end: 40 }, notifyError: false });
  saveClip("p", "c", { revision: "saved", start: 12 });
  expect(request).toHaveBeenLastCalledWith({ method: "patch", url: "clips/p/clips/c/", data: { revision: "saved", start: 12 }, notifyError: false });
  exportClips("p", ["c"]);
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "clips/p/export/", data: { clip_ids: ["c"] }, notifyError: false });
  downloadClip("p", "c");
  expect(request).toHaveBeenLastCalledWith({ url: "clips/p/clips/c/download/", responseType: "blob", notifyError: false });
  retryClipProject("p");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "clips/p/retry/", data: {}, notifyError: false });
});

it("keeps hashtag drafting separate from saving with conflict protection", async () => {
  const { draftClipHashtags, saveClipHashtags } = await import("./apiService");
  draftClipHashtags("p", "c");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "clips/p/clips/c/hashtags/", data: {}, notifyError: false });
  saveClipHashtags("p", "c", ["Topic"], ["Previous"]);
  expect(request).toHaveBeenLastCalledWith({ method: "patch", url: "clips/p/clips/c/hashtags/", data: { hashtags: ["Topic"], previous_hashtags: ["Previous"] }, notifyError: false });
});
