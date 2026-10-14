export const audioDefaults = { trim_start: 0, trim_end: null, delay: 0, fade_in: 0, fade_out: 0, crossfade: 0, volume: 1 };

export function crossfadeReason(scene, next, duration, settings) {
  if (!next) return "This is the last scene.";
  if (!(next.voiceover || next.file) || next.narration_status === "disabled") return "The next scene needs voice audio.";
  if (scene.pause_after > 0) return "Remove the pause after this scene to join the voices.";
  if ((next.audio_settings?.delay || 0) > 0) return "The next voice starts after a delay.";
  const saved = { ...audioDefaults, ...scene.audio_settings };
  const savedEnd = (saved.trim_end ?? duration) - saved.trim_start + saved.delay;
  const draftEnd = (settings.trim_end ?? duration) - settings.trim_start + settings.delay;
  if (scene.timing?.base_duration > savedEnd + 0.02 && draftEnd < scene.timing.base_duration - 0.02) return "The voice ends before this scene. The gap is preserved.";
  return "";
}
