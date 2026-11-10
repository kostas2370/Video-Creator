import { useRef, useState } from "react";

// Share request state while each editor owns its proposal and source validation.
export function useAIRequest() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useRef(false);

  const run = async (request, onSuccess, fallbackMessage) => {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setError("");
    try {
      const response = await request();
      if (!response?.ok) setError(response?.message || fallbackMessage);
      else onSuccess(response.data);
    } catch {
      setError(fallbackMessage);
    } finally {
      running.current = false;
      setBusy(false);
    }
  };

  return { busy, error, run };
}
