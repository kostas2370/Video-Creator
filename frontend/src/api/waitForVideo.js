import { getVideo } from "./apiService";
import { subscribeUpdates } from "./subscribeUpdates";

export const IN_FLIGHT_STATUSES = ["GENERATION", "RENDERING"];
export const isInFlight = status => IN_FLIGHT_STATUSES.includes(status);

export function waitForVideo(id, options = {}) {
  const { onUpdate, intervalMs = 4000, timeoutMs = 3 * 60 * 60 * 1000, maxConsecutiveErrors = 5 } = options;
  let unsubscribe = () => {};
  let timer;
  let finish;
  let finished = false;
  let lastVideo = null;
  let consecutiveErrors = 0;
  const promise = new Promise(resolve => {
    finish = outcome => {
      if (finished) return;
      finished = true;
      unsubscribe();
      clearTimeout(timer);
      resolve({ outcome, video: lastVideo });
    };
    unsubscribe = subscribeUpdates(`videos/${encodeURIComponent(id)}/events/`, {
      load: () => getVideo(id, { notifyError: false }),
      intervalMs,
      onUpdate: video => {
        consecutiveErrors = 0;
        lastVideo = video;
        onUpdate?.(video);
        if (!isInFlight(video.status)) finish("SETTLED");
      },
      onError: () => {
        if (++consecutiveErrors >= maxConsecutiveErrors) finish("UNREACHABLE");
      },
    });
    timer = setTimeout(() => finish("TIMEOUT"), timeoutMs);
  });
  return { promise, cancel: () => finish("CANCELLED") };
}
