import { useEffect, useRef, useState } from "react";
import { readDraftFile, writeDraftFile } from "../utils/draftFiles";

export function useDraftFile(key, expected, onExpectedChange) {
  const [frame, setFrame] = useState({ key, file: null });
  const [loading, setLoading] = useState(!!expected);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const pending = useRef(Promise.resolve());
  useEffect(() => {
    const token = ++sequence.current;
    setFrame({ key, file: null }); setLoading(!!expected); setError("");
    if (!key || !expected) return;
    readDraftFile(key).then(restored => {
      if (sequence.current !== token) return;
      if (restored) setFrame({ key, file: restored }); else setError("Reattach your reference image before continuing; the browser could not recover it.");
    }).catch(() => { if (sequence.current === token) setError("Reattach your reference image before continuing; file recovery is unavailable."); }).finally(() => { if (sequence.current === token) setLoading(false); });
    return () => { sequence.current += 1; };
  }, [key]);
  const change = next => {
    sequence.current += 1;
    setFrame({ key, file: next }); setError(""); setLoading(!!key && !!next);
    onExpectedChange(!!next);
    if (!key) { setLoading(false); return; }
    const token = sequence.current;
    pending.current = pending.current.catch(() => {}).then(() => writeDraftFile(key, next)).then(() => {
      if (sequence.current === token) setLoading(false);
    }).catch(() => {
      if (sequence.current === token) { setLoading(false); setError("The reference image could not be saved for recovery. Choose it again or remove it before continuing."); }
    });
  };
  useEffect(() => {
    if (!loading) return;
    const warn = event => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [loading]);
  return { file: frame.key === key ? frame.file : null, change, loading: frame.key === key ? loading : !!expected, error: frame.key === key ? error : "" };
}
