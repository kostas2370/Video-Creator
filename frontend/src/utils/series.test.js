import { describe, expect, it } from "vitest";
import { defaultSeries, seriesPayload } from "./series";
import { isCreationPath } from "./creationModes";
import { videoLibraryInfo } from "./videoLibrary";

describe("series creation", () => {
  it("highlights creation for the series library and individual workspaces", () => {
    ["/series", "/series/", "/series/example/"].forEach(path => expect(isCreationPath(path)).toBe(true));
    expect(videoLibraryInfo({ video_type: "AI", settings: { creation_mode: "SERIES" } }).mode).toBe("Series episode");
  });
  it("submits only editable fields and normalizes cleared selections", () => {
    const data = seriesPayload({ ...defaultSeries, id: "private-id", scene_count: "8", voice_model: "", intro: null, outro: "outro-1", episode_count: 4 }, null, true);
    expect(data.scene_count).toBe(8);
    expect(data.voice_model).toBeNull();
    expect(data.intro).toBeNull();
    expect(data.outro).toBe("outro-1");
    expect(data.remove_reference).toBe(true);
    expect(data).not.toHaveProperty("id");
    expect(data).not.toHaveProperty("episode_count");
  });
  it("uploads a reference with the profile using multipart data", () => {
    const file = new Blob(["image"], { type: "image/png" });
    const data = seriesPayload(defaultSeries, file);
    expect(data).toBeInstanceOf(FormData);
    expect(data.get("narration")).toBe("true");
    expect(data.get("voice_model")).toBe("");
    expect(data.get("reference_image").size).toBe(file.size);
  });
});
