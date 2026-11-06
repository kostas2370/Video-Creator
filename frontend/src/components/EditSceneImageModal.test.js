// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EditSceneImageModal } from "./EditSceneImageModal";
import { generateSceneImage } from "../api/apiService";
import { toast } from "react-toastify";
vi.mock("../api/apiService", () => ({ generateSceneImage: vi.fn(), updateSceneImage: vi.fn() }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("./GenerationCost", () => ({ GenerationCost: () => null }));
vi.mock("./LibraryPicker", () => ({ LibraryPicker: () => null }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const props = () => ({ showModal: true, setShowModal: vi.fn(), setUpdate: vi.fn(), scene_info: { scene_id: "scene", video_id: "video", video_format: "LANDSCAPE" } });
const generate = () => {
  fireEvent.click(screen.getByRole("button", { name: "Generate with AI" }));
  fireEvent.change(screen.getByLabelText("Visual description"), { target: { value: "A lighthouse" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate visual" }));
};
it("shows a failed background result and keeps the dialog available for retry", async () => {
  generateSceneImage.mockResolvedValueOnce({ ok: false, data: null, message: "Provider unavailable" }).mockResolvedValueOnce({ ok: true, data: { Message: "Ready" } });
  const options = props();
  render(<EditSceneImageModal {...options} />);
  generate();
  expect((await screen.findByRole("alert")).textContent).toBe("Provider unavailable");
  expect(options.setShowModal).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Generate visual" }));
  await waitFor(() => expect(options.setShowModal).toHaveBeenCalledWith(false));
  expect(generateSceneImage).toHaveBeenCalledTimes(2);
});
it("notifies the user if generation fails after closing the dialog", async () => {
  let finish;
  generateSceneImage.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const options = props();
  const view = render(<EditSceneImageModal {...options} />);
  generate();
  fireEvent.click(screen.getByRole("button", { name: "Close editor" }));
  view.rerender(<EditSceneImageModal {...options} showModal={false} />);
  finish({ ok: false, data: null, message: "Generation timed out" });
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Generation timed out"));
});

it("still notifies if the scene editor unmounts while generation is running", async () => {
  let finish;
  generateSceneImage.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const view = render(<EditSceneImageModal {...props()} />);
  generate();
  view.unmount();
  finish({ ok: false, data: null, message: "Generation failed after leaving the scene" });
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Generation failed after leaving the scene"));
});
