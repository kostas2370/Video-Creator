import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("react-toastify", () => ({ toast: { error: vi.fn() } }));
vi.mock("./axiosPrivate", () => ({ axiosPrivateInstance: { request: vi.fn() } }));

import { toast } from "react-toastify";
import { axiosPrivateInstance } from "./axiosPrivate";
import { request } from "./request";

describe("API request results with the upgraded HTTP client", () => {
  beforeEach(() => vi.resetAllMocks());

  it("preserves a successful response and its headers", async () => {
    axiosPrivateInstance.request.mockResolvedValue({
      data: { id: 7 }, status: 200, headers: { "content-type": "application/json" },
    });
    const result = await request({ url: "videos/7/" });
    expect(result).toMatchObject({ ok: true, data: { id: 7 }, status: 200 });
    expect(result.headers["content-type"]).toBe("application/json");
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("accepts a successful deletion with no response body", async () => {
    axiosPrivateInstance.request.mockResolvedValue({ status: 204, headers: {} });
    expect(await request({ method: "delete", url: "videos/7/" }))
      .toMatchObject({ ok: true, data: null, status: 204 });
  });

  it("returns nested validation errors without treating them as video data", async () => {
    axiosPrivateInstance.request.mockRejectedValue({
      response: { status: 400, data: { settings: { voice: ["Choose a voice"] } } },
    });
    expect(await request({ method: "post", url: "videos/", data: {} }))
      .toMatchObject({ ok: false, data: null, status: 400, message: "settings: voice: Choose a voice" });
    expect(toast.error).toHaveBeenCalledWith("settings: voice: Choose a voice", expect.any(Object));
  });

  it("replaces HTML error pages with a readable message", async () => {
    axiosPrivateInstance.request.mockRejectedValue({
      response: { status: 404, data: '<!DOCTYPE html><html><body>Server routes</body></html>' },
    });
    const result = await request({ url: "videos/7/generate_tags/", notifyError: false });
    expect(result.message).toBe("This feature is unavailable on the server. Please refresh and try again.");
    expect(result.message).not.toContain("<html>");
  });

  it("explains missing image endpoints when the server returns an HTML blob", async () => {
    axiosPrivateInstance.request.mockRejectedValue({ response: {
      status: 404,
      data: new Blob(['<!DOCTYPE html><html><body>Not found</body></html>'], { type: "text/html" }),
    } });
    expect(await request({ url: "videos/7/cover_generate/", responseType: "blob", notifyError: false }))
      .toMatchObject({ ok: false, status: 404, message: "This feature is unavailable on the server. Please refresh and try again." });
  });

  it("reports connection failures while keeping background requests quiet", async () => {
    axiosPrivateInstance.request.mockRejectedValue(new Error("Network Error"));
    expect(await request({ url: "videos/", notifyError: false }))
      .toMatchObject({ ok: false, status: null, message: "The server could not be reached" });
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("returns private audio as a blob and reads provider errors from blob responses", async () => {
    const audio = new Blob(["audio"], { type: "audio/mpeg" });
    axiosPrivateInstance.request.mockResolvedValue({ data: audio, status: 200 });
    expect((await request({ url: "voices/1/preview/", method: "post", responseType: "blob" })).data).toBe(audio);
    expect(axiosPrivateInstance.request).toHaveBeenCalledWith(expect.objectContaining({ responseType: "blob" }));
    axiosPrivateInstance.request.mockRejectedValue({ response: { status: 400, data: new Blob([JSON.stringify({ detail: "Switch back to your voice account." })], { type: "application/json" }) } });
    expect(await request({ url: "voices/1/preview/", responseType: "blob", notifyError: false })).toMatchObject({ ok: false, message: "Switch back to your voice account." });
  });
});
