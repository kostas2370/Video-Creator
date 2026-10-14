export const voiceGain = (time, track) => {
  if (time < 0 || time >= track.duration) return 0;
  const incoming = track.fade_in ? Math.min(1, time / track.fade_in) : 1;
  const outgoing = track.fade_out ? Math.min(1, (track.duration - time) / track.fade_out) : 1;
  return (track.volume ?? 1) * incoming * outgoing;
};

export const musicGain = (time, duration, settings, speech) => {
  if (time < 0 || time >= duration) return 0;
  const fadeIn = Math.min(settings.music_fade_in ?? Math.min(4, duration * 0.1), duration / 2);
  const fadeOut = Math.min(settings.music_fade_out ?? Math.min(4, duration * 0.1), duration / 2);
  let gain = (fadeIn ? Math.min(1, time / fadeIn) : 1) * (fadeOut ? Math.min(1, (duration - time) / fadeOut) : 1);
  if (settings.music_ducking) {
    const attack = settings.duck_attack ?? 0.2, release = settings.duck_release ?? 0.8;
    let activity = 0;
    for (const [start, end] of speech) {
      const incoming = Math.max(0, Math.min(1, (time - start + attack) / attack));
      const outgoing = Math.max(0, Math.min(1, (end + release - time) / release));
      activity = Math.max(activity, Math.min(incoming, outgoing));
    }
    gain *= 1 - activity * (1 - (settings.duck_level ?? 0.25));
  }
  return gain * (settings.music_volume ?? 0.07);
};
