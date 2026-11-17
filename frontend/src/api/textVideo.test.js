import { expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { generateTextVideo, generateVideo, generateAudioVideo } from "./apiService";
it("routes scripts and ideas to their respective generation endpoints", () => {
  const data = new FormData();
  data.append("source_text", "Exact narration.");
  generateTextVideo(data);
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "generate/text/", data });
  generateVideo({ message: "An idea" });
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "generate/", data: { message: "An idea" } });
});

it("sends original audio as multipart to the dedicated audio endpoint", () => {
  const data = new FormData();
  data.append("source_audio", new Blob(["audio"], { type: "audio/mpeg" }), "narration.mp3");
  generateAudioVideo(data);
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "generate/audio/", data });
});
