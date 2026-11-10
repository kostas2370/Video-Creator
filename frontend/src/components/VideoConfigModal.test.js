// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VideoConfigModal } from "./VideoConfigModal";
import { updateVideo } from "../api/apiService";
vi.mock("../api/apiService", () => ({ updateVideo: vi.fn(), getIntro: vi.fn(), getOutro: vi.fn(), getAvatars: vi.fn(), getVoices: vi.fn() }));
vi.mock("../hooks/useAssetOptions", () => ({ useAssetOptions: () => ({ items: [], loading: false, error: null, hasMore: false }) }));
vi.mock("./CaptionStyleEditor", () => ({ CaptionStyleEditor: () => null }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const props = (canRetry = false) => ({ showModal: true, setShowModal: vi.fn(), onSaved: vi.fn(), info: { id: "video", title: "Video", voice_model: "voice", avatar: null, status: "FAILED", can_retry_narration: canRetry, settings: {} } });
it("does not resubmit an unchanged voice when saving other settings", async () => {
  updateVideo.mockResolvedValue({ ok: true, status: 200, data: { video: {} } });
  render(<VideoConfigModal {...props()} />);
  expect(screen.queryByRole("button", { name: "Retry narration" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledTimes(1));
  expect(updateVideo.mock.calls[0][1]).not.toHaveProperty("voice_id");
  expect(updateVideo.mock.calls[0][1]).not.toHaveProperty("retry_narration");
});
it("queues narration again only through its explicit retry action", async () => {
  updateVideo.mockResolvedValue({ ok: true, status: 202, data: { video: {} } });
  const options = props(true);
  render(<VideoConfigModal {...options} />);
  fireEvent.click(screen.getByRole("button", { name: "Retry narration" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", { retry_narration: true }));
  await waitFor(() => expect(options.setShowModal).toHaveBeenCalledWith(false));
});

it("saves starting-frame review for a video without character references", async () => {
  updateVideo.mockResolvedValue({ status: 200, data: {} });
  const options = props();
  options.info.mode = "AI";
  options.info.settings = { provider: "gemini-video" };
  render(<VideoConfigModal {...options} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /Review starting frames before generating/ }));
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", expect.objectContaining({ review_starting_frames: true })));
});
