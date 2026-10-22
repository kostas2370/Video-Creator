import { useReducer, useRef } from "react";
import { editorHistoryReducer } from "../utils/editorHistory";
import { sameSceneOrder } from "../utils/editorWorkspace";

export function useUndoHistory(videoId, scenes) {
  const [history, dispatch] = useReducer(editorHistoryReducer, { videoId, entries: [] });
  const activeVideo = useRef(videoId);
  activeVideo.current = videoId;
  const entries = history.videoId === videoId ? history.entries : [];
  const undoEntry = entries.at(-1);
  const undoMatches = !!undoEntry && sameSceneOrder(scenes, undoEntry.after);

  const update = action => {
    // Ignore a response from a project the user has already left.
    if (activeVideo.current === videoId) dispatch({ ...action, videoId });
  };
  return {
    undoEntry,
    undoMatches,
    rememberAction: entry => update({ type: "record", entry }),
    discardLast: entry => update({ type: "consume", entry }),
    clearHistory: () => update({ type: "clear" }),
  };
}
