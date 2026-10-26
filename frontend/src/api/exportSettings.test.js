import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { renderVideo } from "./apiService";

describe("video export API", () => {
  beforeEach(() => vi.clearAllMocks());
  it("submits selected export quality and frame rate together", () => {
    renderVideo("video-1", { export_preset: "HIGH", export_fps: 30 });
    expect(request).toHaveBeenCalledWith({ method: "patch", url: "videos/video-1/render_video/", data: { export_preset: "HIGH", export_fps: 30 }, notifyError: false });
  });
  it("keeps empty render requests compatible with saved project settings", () => {
    renderVideo("video-1");
    expect(request).toHaveBeenCalledWith({ method: "patch", url: "videos/video-1/render_video/", data: {}, notifyError: false });
  });
});
