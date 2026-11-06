import { request } from "./request";

// Follow the queued task while its form is open or retained on this page.
export async function followBackgroundJob(response, { pollUrl = "draft-jobs/", pause = () => new Promise(resolve => setTimeout(resolve, 2000)), maxAttempts = 900 } = {}) {
  if (!response.ok || response.status !== 202) return response;
  let failures = 0;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const result = await request({ url: pollUrl, params: { job: response.data.id }, timeout: 15000, notifyError: false });
    if (!result.ok) {
      const transient = result.status == null || result.status === 408 || result.status === 429 || result.status >= 500;
      if (!transient || failures >= 3) return result;
      failures += 1;
      await pause();
      continue;
    }
    failures = 0;
    if (result.data.status === "SUCCEEDED") return { ...result, data: result.data.result };
    if (result.data.status === "FAILED") return { ...result, ok: false, data: null, message: result.data.error || "Could not finish generation. Please try again." };
    await pause();
  }
  return { ok: false, data: null, message: "Generation is still processing. Check the project before trying again." };
}

export async function runBackgroundDraft(url, data, method = "post") {
  return followBackgroundJob(await request({ method, url, data, notifyError: false }));
}
