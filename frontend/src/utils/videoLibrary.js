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
    mode: video.settings?.creation_mode === "STORY" ? "Story video" : manual ? "Manual edit" : "AI video",
    color: video.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300"
      : video.status === "FAILED" ? "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"
      : "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
    processing,
    canResume: video.status === "FAILED" && !manual && !!video.gpt_answer && !!video.dir_name,
    canDelete: !processing,
  };
}
