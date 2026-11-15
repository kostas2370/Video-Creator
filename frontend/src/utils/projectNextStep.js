export function projectNextStep(video) {
  if (!video) return null;
  const scenes = video.scenes || [];
  if (video.status === "REVIEW") return { title: "Your storyboard is ready", description: "Review the script and visual directions before generating narration and scenes.", label: "Review storyboard", action: "review" };
  if (video.status === "GENERATION") return { title: "Your scenes are being prepared", description: "Generation runs in the background. This page updates automatically; you can come back later." };
  if (video.status === "RENDERING") return { title: "Your video is exporting", description: "Your edit is being rendered. We’ll update this page when your export is ready." };
  if (video.status === "FAILED" && video.render_error?.message) return { title: "Your edit is saved", description: "The last export failed. Review the error below, then retry when you’re ready.", label: "Review & retry export", action: "export" };
  if (video.can_retry_narration) return { title: "Finish your narration", description: "Your scenes are saved. Open narration settings to continue the interrupted voice generation.", label: "Open narration settings", action: "settings" };
  const frame = scenes.find(scene => scene.starting_frame_required && !scene.scene_image?.file);
  if (frame) return { title: frame.starting_frame_status === "approved" ? "Animate your approved frame" : "Review your starting frames", description: "Open the scene to prepare or approve its frame, then start animation when you’re ready.", label: `Open scene ${scenes.indexOf(frame) + 1}`, action: "scene", sceneId: frame.id };
  if (video.status === "FAILED" && video.video_type !== "MANUAL") return { title: "Finish preparing your scenes", description: "Continue generation for missing narration and visuals. Existing media stays in your project.", label: "Generate missing scenes", action: "resume" };
  if (!scenes.length) return { title: "Add your first scene", description: "Bring in a photo or clip, or start with a blank scene and build from there.", label: "Add first scene", action: "add" };
  if (video.status === "FAILED") return { title: "Check your saved scenes", description: "The last operation did not finish. Review your scene media and audio before continuing.", label: "Open first scene", action: "scene", sceneId: scenes[0].id };
  const missingVoice = scenes.find(scene => scene.narration_status === "missing");
  if (missingVoice) return { title: "A scene needs narration", description: "Your script and visuals are saved. Open the scene’s audio tools to retry, or export with the available audio.", label: `Open scene ${scenes.indexOf(missingVoice) + 1}`, action: "scene", sceneId: missingVoice.id };
  return { title: video.status === "COMPLETED" ? "Your export is ready" : "Your video is ready to finish", description: video.status === "COMPLETED" ? "Watch your latest export, or keep editing and export again to include your changes." : "Preview the saved edit, make your final adjustments, then export your video.", label: video.status === "COMPLETED" && video.output ? "Watch latest export" : "Export current edit", action: video.status === "COMPLETED" && video.output ? "watch" : "export" };
}
