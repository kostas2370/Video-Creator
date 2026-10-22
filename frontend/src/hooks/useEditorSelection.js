import { useCallback, useState } from "react";
import { readWorkspace, saveWorkspace } from "../utils/editorWorkspace";

export function useEditorSelection(videoId) {
  const [selection, setSelection] = useState(() => ({
    videoId,
    id: readWorkspace(videoId).sceneId,
  }));
  const selectedId = selection.videoId === videoId
    ? selection.id
    : readWorkspace(videoId).sceneId;

  const select = useCallback(id => {
    setSelection({ videoId, id });
    saveWorkspace(videoId, { sceneId: id });
  }, [videoId]);

  return [selectedId, select];
}
