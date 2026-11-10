// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VideoConfigModal } from "./VideoConfigModal";
import { updateVideo } from "../api/apiService";
vi.mock("../api/apiService", () => ({ updateVideo: vi.fn(), draftNarration: vi.fn(), getIntro: vi.fn(), getOutro: vi.fn(), getAvatars: vi.fn(), getVoices: vi.fn() }));
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

it("enables narration and unlocks the voice picker before saving", async () => {
  updateVideo.mockResolvedValue({ status: 202, data: {} });
  const options = props();
  options.info.settings = { narration: false };
  render(<VideoConfigModal {...options} />);
  expect(screen.getByLabelText("Narration voice").disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox", { name: /^Narration / }));
  expect(screen.getByLabelText("Narration voice").disabled).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", expect.objectContaining({ narration: true })));
  expect(updateVideo.mock.calls[0][1]).not.toHaveProperty("voice_id");
});

it("allows narration to be switched off without choosing another voice", async () => {
  updateVideo.mockResolvedValue({ status: 200, data: {} });
  render(<VideoConfigModal {...props()} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /^Narration / }));
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", expect.objectContaining({ narration: false })));
});

it("restores the saved narration choice when settings are reopened", () => {
  const options = props();
  options.info.settings = { narration: false };
  const { rerender } = render(<VideoConfigModal {...options} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /^Narration / }));
  rerender(<VideoConfigModal {...options} showModal={false} />);
  rerender(<VideoConfigModal {...options} />);
  expect(screen.getByRole("checkbox", { name: /^Narration / }).checked).toBe(false);
});

it("keeps manual projects on their existing caption and uploaded audio controls", async () => {
  updateVideo.mockResolvedValue({ status: 200, data: {} });
  const options = props();
  options.info.video_type = "MANUAL";
  render(<VideoConfigModal {...options} />);
  expect(screen.queryByRole("checkbox", { name: /^Narration / })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledTimes(1));
  expect(updateVideo.mock.calls[0][1]).not.toHaveProperty("narration");
});

it("reviews AI narration before saving or generating speech", async () => {
  const { draftNarration } = await import("../api/apiService");
  const options = props();
  options.info.settings = { narration: false };
  options.info.scenes = [{ id: "scene-1", text: "A bank counter.", scene_image: { prompt: "A bank counter.", with_audio: true } }];
  const row = { scene_id: "scene-1", before: "A bank counter.", before_visual: "A bank counter.", text: "Where does your deposit go?" };
  draftNarration.mockResolvedValue({ ok: true, data: { scenes: [row] } });
  updateVideo.mockResolvedValue({ status: 202, data: {} });
  render(<VideoConfigModal {...options} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /^Narration / }));
  expect(screen.getByRole("button", { name: "Save and generate speech" }).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Write narration from scenes" }));
  const text = await screen.findByLabelText("Narration for scene 1");
  expect(text.value).toBe(row.text);
  expect(updateVideo).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Save and generate speech" }).disabled).toBe(true);
  fireEvent.change(text, { target: { value: "Your bank balance tells a story." } });
  fireEvent.click(screen.getByRole("checkbox", { name: /I reviewed the narration/ }));
  fireEvent.click(screen.getByRole("button", { name: "Save and generate speech" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", expect.objectContaining({ narration: true, narration_scenes: [{ ...row, text: "Your bank balance tells a story." }] })));
});

it("lets existing text be reviewed without an AI writing request", async () => {
  const { draftNarration } = await import("../api/apiService");
  const options = props();
  options.info.settings = { narration: false };
  options.info.scenes = [{ id: "scene-1", text: "Existing narration.", scene_image: { prompt: "Visual description." } }];
  render(<VideoConfigModal {...options} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /^Narration / }));
  fireEvent.click(screen.getByRole("button", { name: "Use existing text" }));
  expect(screen.getByLabelText("Narration for scene 1").value).toBe("Existing narration.");
  expect(draftNarration).not.toHaveBeenCalled();
  expect(updateVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("checkbox", { name: /I reviewed the narration/ }));
  expect(screen.getByRole("button", { name: "Save and generate speech" }).disabled).toBe(false);
  fireEvent.change(screen.getByLabelText("Narration for scene 1"), { target: { value: "Edited again." } });
  expect(screen.getByRole("button", { name: "Save and generate speech" }).disabled).toBe(true);
});

it("allows character dialogue automatically with narration off and saves the audio mix separately", async () => {
  const options = props();
  options.info.settings = { narration: false };
  updateVideo.mockResolvedValue({ status: 200, data: {} });
  render(<VideoConfigModal {...options} />);
  expect(screen.getByRole("option", { name: /Automatic.*character dialogue allowed/ })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Generated clip sound"), { target: { value: "DIALOGUE" } });
  fireEvent.change(screen.getByLabelText("Background music volume"), { target: { value: "0" } });
  fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(updateVideo).toHaveBeenCalledWith("video", expect.objectContaining({ narration: false, video_audio_mode: "DIALOGUE", music_volume: 0 })));
});
