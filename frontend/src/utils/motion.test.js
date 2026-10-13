import { describe, expect, it } from "vitest";
import { imageMotion } from "./motion";

describe("image motion in preview", () => {
  it("holds the final transform during pauses and outgoing dissolves", () => {
    for (const style of ["ZOOM_IN", "ZOOM_OUT", "PAN_LEFT", "PAN_RIGHT", "PAN_UP", "PAN_DOWN"]) {
      const segment = { base_duration: 2, motion_style: style, motion_intensity: "STRONG" };
      expect(imageMotion(segment, 0)).not.toEqual(imageMotion(segment, 2));
      expect(imageMotion(segment, 2)).toEqual(imageMotion(segment, 4));
    }
  });
  it("uses a filled frame at the start, middle and end of each pan", () => {
    const segment = { base_duration: 2, motion_style: "PAN_RIGHT", motion_intensity: "STRONG" };
    expect(imageMotion(segment, 0).transform).toBe("translate(-10%, 0%) scale(1.2)");
    expect(imageMotion(segment, 2).transform).toBe("translate(10%, 0%) scale(1.2)");
  });
  it("leaves scenes without motion unchanged", () => {
    expect(imageMotion({ base_duration: 2 }, 1).transform).toBe("translate(0%, 0%) scale(1)");
  });
});
