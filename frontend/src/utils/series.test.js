import { describe, expect, it } from "vitest";
import { defaultSeries, seriesPayload, episodeMemoryReducer } from "./series";
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
    expect(JSON.parse(data.get("cast"))).toEqual([]);
  });
  it("preserves structured cast and format when saving with a reference", () => {
    const cast = [{ id: "cast-1", name: "Milo", appearance: "Orange fox", wardrobe: "Teal scarf", personality: "Curious", relationships: "Rival of Rin" }];
    const profile = { ...defaultSeries, cast, story_format: "SERIAL_DRAMA" };
    expect(seriesPayload(profile).cast).toEqual(cast);
    const uploaded = seriesPayload(profile, new Blob(["image"], { type: "image/png" }));
    expect(JSON.parse(uploaded.get("cast"))).toEqual(cast);
    expect(uploaded.get("story_format")).toBe("SERIAL_DRAMA");
  });
});


describe("episode memory draft synchronization", () => {
  it("refreshes clean memory from the server", () => {
    expect(episodeMemoryReducer({ draft: "Old", baseline: "Old" }, { type: "remote", value: "New" })).toEqual({ draft: "New", baseline: "New" });
  });
  it("preserves unsaved work and its original conflict baseline across refresh", () => {
    const edited = episodeMemoryReducer({ draft: "Old", baseline: "Old" }, { type: "edit", value: "My unsaved facts" });
    expect(episodeMemoryReducer(edited, { type: "remote", value: "Another editor’s facts" })).toEqual({ draft: "My unsaved facts", baseline: "Old" });
  });
  it("accepts a successful save or an explicit load of the saved memory", () => {
    for (const type of ["saved", "load"]) expect(episodeMemoryReducer({ draft: "Draft", baseline: "Old" }, { type, value: "Saved" })).toEqual({ draft: "Saved", baseline: "Saved" });
  });
});

it("keeps the reviewed script and saved conflict baseline when generating a memory draft", () => {
  const state = { draft: "Manual correction", baseline: "Saved", sourceHash: "old" };
  const generated = episodeMemoryReducer(state, { type: "generated", value: "Updated", sourceHash: "new" });
  expect(generated).toEqual({ draft: "Updated", baseline: "Saved", sourceHash: "new" });
  expect(episodeMemoryReducer(generated, { type: "remote", value: "Other", sourceHash: "later" })).toEqual(generated);
  expect(episodeMemoryReducer(generated, { type: "generated", value: state.draft, sourceHash: state.sourceHash })).toEqual(state);
});
