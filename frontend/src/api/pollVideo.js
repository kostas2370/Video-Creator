import { getVideo } from "./apiService";

export const IN_FLIGHT_STATUSES = ["GENERATION", "RENDERING"];

export const isInFlight = (status) => IN_FLIGHT_STATUSES.includes(status);

const DEFAULT_INTERVAL_MS = 4000;
const DEFAULT_TIMEOUT_MS = 3 * 60 * 60 * 1000;
const DEFAULT_MAX_ERRORS = 5;

export function pollVideo(id, options = {}) {
  const {
    onUpdate,
    intervalMs = DEFAULT_INTERVAL_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    maxConsecutiveErrors = DEFAULT_MAX_ERRORS,
  } = options;

  let cancelled = false;
  let timer = null;

  const promise = new Promise((resolve) => {
    const startedAt = Date.now();
    let consecutiveErrors = 0;
    let lastVideo = null;

    const tick = async () => {
      if (cancelled) return;

      const video = await getVideo(id);

      if (cancelled) return;

      if (!video || !video.status) {
        consecutiveErrors += 1;
        if (consecutiveErrors >= maxConsecutiveErrors) {
          resolve({ outcome: "UNREACHABLE", video: lastVideo });
          return;
        }
      } else {
        consecutiveErrors = 0;
        lastVideo = video;

        if (onUpdate) onUpdate(video);

        if (!isInFlight(video.status)) {
          resolve({ outcome: "SETTLED", video });
          return;
        }
      }

      if (Date.now() - startedAt > timeoutMs) {
        resolve({ outcome: "TIMEOUT", video: lastVideo });
        return;
      }

      timer = setTimeout(tick, intervalMs);
    };

    tick();
  });

  return {
    promise,
    cancel: () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    },
  };
}
