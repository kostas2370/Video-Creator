// Follow a background operation without holding an API request open.
export async function waitForSceneOperation(load, { pause = () => new Promise(resolve => setTimeout(resolve, 2000)), maxAttempts = 900 } = {}) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const response = await load();
    if (!response.ok) return response;
    if (response.data.status === "SUCCEEDED") return { ...response, data: response.data.result };
    if (response.data.status === "FAILED") return { ...response, ok: false, data: null, message: response.data.error || "Could not finish the scene operation." };
    await pause();
  }
  return { ok: false, data: null, message: "This scene is still processing. Refresh the video to check its progress." };
}
