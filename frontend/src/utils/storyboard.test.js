import { describe, it, expect } from "vitest";
import { editableStoryboard } from "./storyboard";

describe("scene-based storyboards", () => {
  it("keeps a scene paragraph and its visual shots together without changing saved data", () => {
    const script = { title: "Coffee", scenes: [{ scene: "Roasting", narration: "Beans heat up. Their aroma changes. Then they cool.", image_description: "A roaster", additional_image_descriptions: ["Cooling beans"] }] };
    const draft = editableStoryboard(script);
    expect(draft.scenes).toHaveLength(1);
    expect(draft.scenes[0].narration).toBe(script.scenes[0].narration);
    draft.scenes[0].additional_image_descriptions[0] = "New visual";
    expect(script.scenes[0].additional_image_descriptions[0]).toBe("Cooling beans");
  });
  it("opens each legacy narration entry as an editable scene without merging existing content", () => {
    const script = { title: "Old project", scenes: [{ scene: "Opening", sentences: [{ sentence: "First line.", image_description: "First visual", shot_plan: { shot_size: "WIDE" } }, { sentence: "Second line.", image_description: "Second visual" }] }] };
    const draft = editableStoryboard(script);
    expect(draft.scenes.map(scene => scene.narration)).toEqual(["First line.", "Second line."]);
    expect(draft.scenes[0].shot_plan.shot_size).toBe("WIDE");
    expect(draft.scenes.every(scene => !("sentences" in scene) && !("sentence" in scene))).toBe(true);
    expect(script.scenes[0].sentences).toHaveLength(2);
  });
  it("keeps legacy silent scenes silent", () => {
    const draft = editableStoryboard({ scenes: [{ scene: "Quiet", sentences: [{ image_description: "Forest" }] }] });
    expect(draft.scenes[0]).toEqual({ scene: "Quiet", image_description: "Forest" });
  });
});
