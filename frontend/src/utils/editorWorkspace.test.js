import { afterEach, describe, expect, it, vi } from "vitest";
import { readWorkspace, saveWorkspace, rememberedScene, sameSceneOrder } from "./editorWorkspace";

afterEach(() => vi.unstubAllGlobals());

describe("editor workspace recovery", () => {
  it("keeps each project's selection and panels separate and merges preferences", () => {
    const values = new Map();
    vi.stubGlobal("localStorage", { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) });
    saveWorkspace("first", { sceneId: "scene-2" });
    saveWorkspace("first", { adjustScene: true });
    saveWorkspace("second", { sceneId: "scene-9" });
    expect(readWorkspace("first")).toEqual({ sceneId: "scene-2", adjustScene: true });
    expect(readWorkspace("second").sceneId).toBe("scene-9");
  });
  it("continues editing with corrupted or blocked browser storage", () => {
    vi.stubGlobal("localStorage", { getItem: () => "{broken", setItem: () => { throw new Error("Storage blocked"); } });
    expect(readWorkspace("first")).toEqual({});
    expect(() => saveWorkspace("first", { sceneId: "scene-2" })).not.toThrow();
  });
  it("falls back if the remembered scene was removed", () => {
    const scenes = [{ id: "first" }, { id: "second" }];
    expect(rememberedScene(scenes, "second")).toBe(scenes[1]);
    expect(rememberedScene(scenes, "deleted")).toBe(scenes[0]);
    expect(rememberedScene([], "deleted")).toBeUndefined();
  });
  it("rejects an undo after scenes were added, removed, or moved elsewhere", () => {
    const scenes = [{ id: "first" }, { id: "second" }];
    expect(sameSceneOrder(scenes, ["first", "second"])).toBe(true);
    expect(sameSceneOrder(scenes, ["second", "first"])).toBe(false);
    expect(sameSceneOrder(scenes, ["first"])).toBe(false);
    expect(sameSceneOrder([], [])).toBe(true);
  });
});
