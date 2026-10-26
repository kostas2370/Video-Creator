import { describe, it, expect } from "vitest";
import { shotAtTime, shotDurations, moveShotBoundary } from "./shots";

describe("scene shot timing", () => {
  it("switches at the cut and holds the final shot at the end", () => {
    const shots = [{ id: "a", start: 0, duration: 3 }, { id: "b", start: 3, duration: 7 }];
    expect(shotAtTime(shots, 2.99).id).toBe("a");
    expect(shotAtTime(shots, 3).id).toBe("b");
    expect(shotAtTime(shots, 10).id).toBe("b");
  });
  it("moves only the adjacent cut while preserving total scene length", () => {
    const shots = [{ timing_weight: 1 }, { timing_weight: 1 }, { timing_weight: 1 }];
    const changed = moveShotBoundary(shots, 1, 9, 12);
    expect(shotDurations(changed, 12)).toEqual([4, 5, 3]);
    expect(shotDurations(changed, 24)).toEqual([8, 10, 6]);
  });
  it("keeps both adjacent shots positive at extreme cut positions", () => {
    const result = shotDurations(moveShotBoundary([{ timing_weight: 1 }, { timing_weight: 1 }], 0, 100, 4), 4);
    expect(result[0] + result[1]).toBeCloseTo(4);
    expect(result[1]).toBeGreaterThan(0);
  });
});
