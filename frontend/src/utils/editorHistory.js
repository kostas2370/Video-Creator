export const UNDO_HISTORY_LIMIT = 20;

export function editorHistoryReducer(state, action) {
  const current = state.videoId === action.videoId
    ? state
    : { videoId: action.videoId, entries: [] };
  switch (action.type) {
    case "record":
      return {
        ...current,
        entries: [...current.entries, action.entry].slice(-UNDO_HISTORY_LIMIT),
      };
    case "consume":
      // A completed request must not consume an entry recorded afterward.
      return current.entries.at(-1) === action.entry
        ? { ...current, entries: current.entries.slice(0, -1) }
        : current;
    case "clear":
      return { ...current, entries: [] };
    default:
      return current;
  }
}
