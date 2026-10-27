import { beforeEach, expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { draftSeriesEpisode, saveEpisodeMemory, retrySeriesEpisode } from "./apiService";

beforeEach(() => vi.clearAllMocks());
it("uses separate endpoints for episode drafting, memory and recovery", () => {
  draftSeriesEpisode("series-1", "A new discovery");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "series/series-1/episodes/", data: { idea: "A new discovery" }, notifyError: false });
  saveEpisodeMemory("series-1", "episode-2", "Milo found a lantern");
  expect(request).toHaveBeenLastCalledWith({ method: "patch", url: "series/series-1/episodes/episode-2/", data: { summary: "Milo found a lantern" }, notifyError: false });
  retrySeriesEpisode("series-1", "episode-2");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "series/series-1/episodes/episode-2/retry/", data: {}, notifyError: false });
});
