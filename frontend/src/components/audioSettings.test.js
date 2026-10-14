import { describe, expect, it } from "vitest";
import { audioDefaults, crossfadeReason } from "./audioSettings";

const next = { file: "/voice.wav", narration_status: "available", audio_settings: {} };
const scene = { pause_after: 0, timing: { base_duration: 4 }, audio_settings: {} };
describe("crossfade availability", () => {
  it("allows adjacent voices and a trimmed still scene", () => {
    expect(crossfadeReason(scene, next, 4, audioDefaults)).toBe("");
    expect(crossfadeReason(scene, next, 4, { ...audioDefaults, trim_end: 2 })).toBe("");
  });
  it("explains last scenes, silent next scenes, and pauses", () => {
    expect(crossfadeReason(scene, undefined, 4, audioDefaults)).toMatch(/last scene/);
    expect(crossfadeReason(scene, { file: "" }, 4, audioDefaults)).toMatch(/needs voice/);
    expect(crossfadeReason({ ...scene, pause_after: 1 }, next, 4, audioDefaults)).toMatch(/pause/);
  });
  it("preserves held frames and next-voice delays", () => {
    expect(crossfadeReason({ ...scene, timing: { base_duration: 6 } }, next, 4, audioDefaults)).toMatch(/gap/);
    expect(crossfadeReason(scene, { ...next, audio_settings: { delay: 1 } }, 4, audioDefaults)).toMatch(/delay/);
  });
});
