import { useEffect, useState } from "react";

export function useObjectUrl(file) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const next = file ? URL.createObjectURL(file) : "";
    setUrl(next);
    return () => { if (next) URL.revokeObjectURL(next); };
  }, [file]);
  return url;
}
