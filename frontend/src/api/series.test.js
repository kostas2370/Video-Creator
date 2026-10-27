import { beforeEach, expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { draftSeriesEpisode, saveEpisodeMemory, draftEpisodeMemory, retrySeriesEpisode } from "./apiService";

beforeEach(() => vi.clearAllMocks());
it("uses separate endpoints for episode drafting, memory and recovery", () => {
  draftSeriesEpisode("series-1", "A new discovery");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "series/series-1/episodes/", data: { idea: "A new discovery" }, notifyError: false });
  saveEpisodeMemory("series-1", "episode-2", "Milo found a lantern");
  expect(request).toHaveBeenLastCalledWith({ method: "patch", url: "series/series-1/episodes/episode-2/", data: { summary: "Milo found a lantern" }, notifyError: false });
  retrySeriesEpisode("series-1", "episode-2");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "series/series-1/episodes/episode-2/retry/", data: {}, notifyError: false });
});

it("drafts memory without saving and sends the reviewed script on explicit save", () => {
  draftEpisodeMemory("series-1", "episode-2", "My correction");
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "series/series-1/episodes/episode-2/draft_memory/", data: { summary: "My correction" }, notifyError: false });
  saveEpisodeMemory("series-1", "episode-2", "Updated", "Saved", "script-fingerprint");
  expect(request).toHaveBeenLastCalledWith({ method: "patch", url: "series/series-1/episodes/episode-2/", data: { summary: "Updated", previous_summary: "Saved", script_hash: "script-fingerprint" }, notifyError: false });
});
