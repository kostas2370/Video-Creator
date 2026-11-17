import { expect, it, vi } from "vitest";
vi.mock("./request", () => ({ request: vi.fn() }));
import { request } from "./request";
import { generateTextVideo, generateVideo } from "./apiService";
it("routes scripts and ideas to their respective generation endpoints", () => {
  const data = new FormData();
  data.append("source_text", "Exact narration.");
  generateTextVideo(data);
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "generate/text/", data });
  generateVideo({ message: "An idea" });
  expect(request).toHaveBeenLastCalledWith({ method: "post", url: "generate/", data: { message: "An idea" } });
});
