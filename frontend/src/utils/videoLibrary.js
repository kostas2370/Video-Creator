export const libraryStatuses = [
  { value: "", label: "All statuses" },
  { value: "COMPLETED", label: "Export ready" },
  { value: "READY", label: "Ready to export" },
  { value: "REVIEW", label: "Review script" },
  { value: "GENERATION", label: "Creating scenes" },
  { value: "RENDERING", label: "Exporting" },
  { value: "FAILED", label: "Needs attention" },
];

export function videoLibraryInfo(video) {
  const processing = ["GENERATION", "RENDERING"].includes(video.status);
  const manual = video.video_type === "MANUAL";
  return {
    label: libraryStatuses.find(item => item.value === video.status)?.label || "Project",
    mode: video.settings?.creation_mode === "SERIES" ? "Series episode" : video.settings?.creation_mode === "STORY" ? "Story video" : manual ? "Manual edit" : "AI video",
    color: video.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
      : video.status === "FAILED" ? "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"
      : "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    processing,
    canResume: video.status === "FAILED" && !video.render_error?.message && !manual && !!video.gpt_answer && !!video.dir_name,
    canDelete: !processing,
  };
}


export const libraryTypes = [
  { value: "", label: "All types" },
  { value: "AI", label: "AI videos" },
  { value: "MANUAL", label: "Manual edits" },
  { value: "STORY", label: "Story videos" },
  { value: "SERIES", label: "Series episodes" },
];

export const librarySorts = [
  { value: "-updated_at", label: "Recently edited" },
  { value: "-created_at", label: "Newest created" },
  { value: "created_at", label: "Oldest created" },
  { value: "title", label: "Title A–Z" },
  { value: "-title", label: "Title Z–A" },
];

export function libraryProgress(video) {
  if (video.status === "RENDERING") return { title: "Exporting your video", steps: [], description: "Combining your scenes, audio, and captions. You can leave this page while it finishes." };
  if (video.status !== "GENERATION") return { title: video.status === "FAILED" ? "Generation needs attention" : "Scenes prepared", steps: [], description: "Open the editor to review your project." };
  const scenes = video.scenes || [];
  if (!scenes.length) return { title: "Preparing your scenes", steps: [], description: "Setting up the script and scene assets. Progress updates automatically." };
  const visuals = scenes.filter(scene => !!scene.scene_image?.file).length;
  const narrated = scenes.filter(scene => scene.narration_status !== "disabled");
  const steps = [{ label: "Visuals prepared", done: visuals, total: scenes.length }];
  // Only report narration counts when the API provides its availability status.
  if (narrated.length && narrated.every(scene => ["available", "missing"].includes(scene.narration_status))) steps.push({ label: "Narration prepared", done: narrated.filter(scene => scene.narration_status === "available").length, total: narrated.length });
  return { title: steps.every(step => step.done === step.total) ? "Finishing scene preparation" : "Preparing visuals and audio", steps, description: "Saved assets update as they become available. You can come back later." };
}

export function libraryEmptyState(query) {
  const constraints = [];
  if (query.search) constraints.push(`matching “${query.search}”`);
  if (query.creation_mode) constraints.push(`of type “${libraryTypes.find(type => type.value === query.creation_mode)?.label || query.creation_mode}”`);
  if (query.status) constraints.push(`with status “${libraryStatuses.find(status => status.value === query.status)?.label || query.status}”`);
  if (query.is_favorite && !constraints.length) return { title: "No favorites yet", description: "Star a video in All videos to keep it here for easy access.", action: "Browse all videos" };
  if (query.is_favorite) constraints.unshift("in Favorites");
  if (constraints.length) return { title: "No videos match your selection", description: `We couldn’t find any videos ${constraints.join(" ")}. Try fewer filters or browse your full library.`, action: "Reset filters" };
  return { title: "Your first video starts with an idea", description: "Create a story, bring your own clips, or let AI help you get started." };
}
