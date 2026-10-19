import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { getVideos, toggleVideoFavorite } from "./apiService";

describe("video library API", () => {
  beforeEach(() => vi.clearAllMocks());
  it("sends combined filters and sorting with search and pagination", () => {
    getVideos("dog", 2, "COMPLETED", { creation_mode: "STORY", is_favorite: true, ordering: "-updated_at" });
    expect(request).toHaveBeenCalledWith({ url: "videos/", params: {
      search: "dog", page: 2, status: "COMPLETED", creation_mode: "STORY", is_favorite: true, ordering: "-updated_at",
    } });
  });
  it("toggles a favorite with a body-free PATCH on each press", () => {
    toggleVideoFavorite("video-1");
    toggleVideoFavorite("video-1");
    expect(request).toHaveBeenNthCalledWith(1, { method: "patch", url: "videos/video-1/favorite/", data: undefined });
    expect(request).toHaveBeenNthCalledWith(2, { method: "patch", url: "videos/video-1/favorite/", data: undefined });
  });
});
