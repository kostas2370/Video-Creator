import { getVideo } from "./apiService";

// Generation and rendering run on a Celery worker now. The API answers 202 straight
// away with a video in GENERATION / RENDERING, and the only way to learn the outcome
// is to re-read the video until its status settles.
export const IN_FLIGHT_STATUSES = ["GENERATION", "RENDERING"];

export const isInFlight = (status) => IN_FLIGHT_STATUSES.includes(status);

const DEFAULT_INTERVAL_MS = 4000;
// The backend gives up on a job after 3h (VIDEO_TASK_STALE_AFTER) and marks it FAILED,
// so there is no point watching for longer than that.
const DEFAULT_TIMEOUT_MS = 3 * 60 * 60 * 1000;
const DEFAULT_MAX_ERRORS = 5;

/**
 * Watch a video until it leaves GENERATION / RENDERING.
 *
 * Returns { promise, cancel }. The promise always resolves, never rejects:
 *   { outcome: "SETTLED",     video }  status is READY / COMPLETED / FAILED
 *   { outcome: "UNREACHABLE", video }  the API stopped answering
 *   { outcome: "TIMEOUT",     video }  still in flight when we gave up
 *
 * Call cancel() on unmount — otherwise the interval outlives the component.
 */
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

      // getVideo swallows errors and resolves undefined, so a missing status is the
      // only signal we get that the request did not land.
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
