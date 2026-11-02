import { describe, expect, it } from "vitest";
import { animationProgress, cameraAt, overlayEntrance, photoAnimationPlan } from "./photoAnimation";
import { imageMotion } from "./motion";
import fixtures from "../../../backend/apps/videomanagement/tests/composer/photo_animation_fixtures.json";

describe("photo animations", () => {
  it("matches the backend's timeline fixtures", () => {
    for (const row of fixtures) expect(photoAnimationPlan(row.preset, row.intensity, row.id, row.accents)).toEqual(row.plan);
  });
  it("holds the final camera and particle frame through pauses at either export frame rate", () => {
    for (const fps of [24, 30]) {
      const plan = photoAnimationPlan("PLAYFUL", "STRONG", fixtures[0].id);
      const segment = { photo_animation: plan, base_duration: .63, fps };
      expect(imageMotion(segment, .63)).toEqual(imageMotion(segment, 4));
      expect(animationProgress(.63, .63, fps)).toBe(1);
      expect(cameraAt(plan.camera, 1).scale).toBeGreaterThan(1);
    }
  });
  it("can disable all decorative particles while keeping the camera animation", () => {
    const plan = photoAnimationPlan("PLAYFUL", "SUBTLE", fixtures[0].id, false);
    expect(plan.particles).toEqual([]);
    expect(plan.camera.length).toBeGreaterThan(1);
    expect(photoAnimationPlan("NONE", "SUBTLE", fixtures[0].id)).toBeNull();
  });
  it("keeps every camera crop inside its photo", () => {
    for (const preset of ["PLAYFUL", "DRAMATIC", "CALM", "EXPLAINER"]) {
      const plan = photoAnimationPlan(preset, "STRONG", fixtures[0].id);
      for (let i = 0; i <= 100; i++) {
        const frame = cameraAt(plan.camera, i / 100);
        expect(Math.abs(frame.x)).toBeLessThanOrEqual((frame.scale - 1) / 2 + 1e-8);
        expect(Math.abs(frame.y)).toBeLessThanOrEqual((frame.scale - 1) / 2 + 1e-8);
      }
    }
  });
  it("replays text entrances after seeking and completes them even for short overlays", () => {
    for (const preset of ["PLAYFUL", "DRAMATIC", "CALM", "EXPLAINER"]) {
      expect(overlayEntrance(preset, .1, .1)).toEqual({ scale: 1, opacity: 1, dy: 0 });
      expect(overlayEntrance(preset, 0, .1)).not.toEqual({ scale: 1, opacity: 1, dy: 0 });
    }
  });
});
