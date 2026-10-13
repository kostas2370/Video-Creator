import { describe, expect, it } from "vitest";
import { musicGain, voiceGain } from "./audioEnvelope";

describe("audio playback envelopes", () => {
  it("fades voice clips and keeps audio outside the trim silent", () => {
    const track = { duration: 4, fade_in: 1, fade_out: 1, volume: 0.8 };
    expect(voiceGain(-1, track)).toBe(0);
    expect(voiceGain(0.5, track)).toBeCloseTo(0.4);
    expect(voiceGain(2, track)).toBeCloseTo(0.8);
    expect(voiceGain(3.5, track)).toBeCloseTo(0.4);
    expect(voiceGain(4, track)).toBe(0);
  });
  it("ducks smoothly during speech, recovering in silence", () => {
    const settings = { music_volume: 0.8, music_ducking: true, duck_level: 0.25, duck_attack: 0.2, duck_release: 0.8, music_fade_in: 0, music_fade_out: 0 };
    expect(musicGain(1, 10, settings, [[2, 4]])).toBeCloseTo(0.8);
    expect(musicGain(1.9, 10, settings, [[2, 4]])).toBeCloseTo(0.5);
    expect(musicGain(3, 10, settings, [[2, 4]])).toBeCloseTo(0.2);
    expect(musicGain(4.4, 10, settings, [[2, 4]])).toBeCloseTo(0.5);
    expect(musicGain(5, 10, settings, [[2, 4]])).toBeCloseTo(0.8);
  });
  it("overlapping speech does not multiply the ducking reduction", () => {
    expect(musicGain(3, 10, { music_ducking: true, music_volume: 1, music_fade_in: 0, music_fade_out: 0 }, [[2, 4], [3, 5]])).toBe(0.25);
  });
  it("fades music at its boundaries and returns silence outside the scene region", () => {
    const settings = { music_volume: 1, music_fade_in: 2, music_fade_out: 2 };
    expect(musicGain(-1, 10, settings, [])).toBe(0);
    expect(musicGain(1, 10, settings, [])).toBe(0.5);
    expect(musicGain(9, 10, settings, [])).toBe(0.5);
    expect(musicGain(10, 10, settings, [])).toBe(0);
  });
});
