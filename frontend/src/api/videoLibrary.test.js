import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { getVideos, setVideoFavorite } from "./apiService";

describe("video library API", () => {
  beforeEach(() => vi.clearAllMocks());
  it("sends combined filters and sorting with search and pagination", () => {
    getVideos("dog", 2, "COMPLETED", { creation_mode: "STORY", is_favorite: true, ordering: "-updated_at" });
    expect(request).toHaveBeenCalledWith({ url: "videos/", params: {
      search: "dog", page: 2, status: "COMPLETED", creation_mode: "STORY", is_favorite: true, ordering: "-updated_at",
    } });
  });
  it("explicitly saves both favorite and unfavorite without updating video settings", () => {
    setVideoFavorite("video-1", true);
    setVideoFavorite("video-1", false);
    expect(request).toHaveBeenNthCalledWith(1, { method: "patch", url: "videos/video-1/favorite/", data: { is_favorite: true } });
    expect(request).toHaveBeenNthCalledWith(2, { method: "patch", url: "videos/video-1/favorite/", data: { is_favorite: false } });
  });
});
