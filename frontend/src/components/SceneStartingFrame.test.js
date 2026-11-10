// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Scene } from "./Scene";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });
it("shows a saved starting frame after video failure and retries the saved description", async () => {
  const retry = vi.spyOn(api, "generateSceneImage").mockResolvedValue({ ok: true });
  const updated = vi.fn();
  render(<Scene scene={{ id: "scene-1", video: "video-1", text: "Milo finds a lantern", narration_status: "disabled", starting_frame: "/media/library/start.png", starting_frame_description: "Milo at the forest gate", scene_image: { file: null } }} manual setUpdated={updated} />);
  expect(screen.getByAltText("Scene 1 saved starting frame").getAttribute("src")).toContain("/media/library/start.png");
  fireEvent.click(screen.getByRole("button", { name: "Retry video with saved frame" }));
  await waitFor(() => expect(updated).toHaveBeenCalledWith(true));
  expect(retry.mock.calls[0][0]).toBe("scene-1");
  expect(retry.mock.calls[0][1].get("image_description")).toBe("Milo at the forest gate");
});

const reviewScene = {
  id: "scene-1", video: "video-1", text: "Milo finds a lantern", narration_status: "disabled",
  starting_frame_required: true, starting_asset: "asset-1", starting_frame: "/media/library/start.png",
  starting_frame_description: "Milo at the forest gate", starting_frame_status: "needs_review",
  scene_image: { file: "/media/old.mp4" },
};

it("requires approval before offering a separate animation request", async () => {
  const update = vi.spyOn(api, "updateStartingFrame").mockResolvedValue({ ok: true });
  const generate = vi.spyOn(api, "generateSceneImage").mockResolvedValue({ ok: true });
  const updated = vi.fn();
  const { rerender } = render(<Scene scene={reviewScene} manual setUpdated={updated} />);
  expect(screen.queryByRole("button", { name: "Animate approved frame" })).toBeNull();
  expect(screen.getByText("Change frame").closest("details").open).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Approve starting frame" }));
  await waitFor(() => expect(updated).toHaveBeenCalledWith(true));
  expect(update).toHaveBeenCalledTimes(1);
  expect(update.mock.calls[0][1].get("operation")).toBe("approve");
  expect(update.mock.calls[0][1].get("asset_id")).toBe("asset-1");
  rerender(<Scene scene={{ ...reviewScene, starting_frame_status: "approved" }} manual setUpdated={updated} />);
  fireEvent.click(screen.getByRole("button", { name: "Animate approved frame" }));
  await waitFor(() => expect(update).toHaveBeenCalledTimes(2));
  expect(update.mock.calls[1][1].get("operation")).toBe("animate");
  expect(generate).not.toHaveBeenCalled();
});

it("prepares a changed image without animation and blocks unsaved edits", async () => {
  const generate = vi.spyOn(api, "generateSceneImage").mockResolvedValue({ ok: true });
  const update = vi.spyOn(api, "updateStartingFrame").mockResolvedValue({ ok: true });
  const updated = vi.fn();
  render(<Scene scene={{ ...reviewScene, starting_frame_status: "approved" }} manual setUpdated={updated} />);
  fireEvent.click(screen.getByText("Change frame"));
  fireEvent.change(screen.getByRole("textbox", { name: "Scene 1 starting frame description" }), { target: { value: "Milo in the workshop" } });
  expect(screen.getByRole("button", { name: "Animate approved frame" }).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Regenerate starting frame" }));
  await waitFor(() => expect(updated).toHaveBeenCalledWith(true));
  expect(generate.mock.calls[0][1].get("image_description")).toBe("Milo in the workshop");
  expect(update).not.toHaveBeenCalled();
});

it("uploads replacement frames for review and shows failed actions", async () => {
  const update = vi.spyOn(api, "updateStartingFrame").mockResolvedValue({ ok: false, message: "Could not upload the image" });
  render(<Scene scene={reviewScene} manual setUpdated={vi.fn()} />);
  fireEvent.click(screen.getByText("Change frame"));
  fireEvent.click(screen.getByText("Upload a frame instead"));
  const file = new File(["image"], "replacement.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText("Scene 1 replacement starting frame"), { target: { files: [file] } });
  expect(screen.getByRole("button", { name: "Approve starting frame" }).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Save starting frame" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Could not upload"));
  expect(update.mock.calls[0][1].get("operation")).toBe("upload");
  expect(update.mock.calls[0][1].get("image").name).toBe("replacement.png");
});

it("offers retry for a failed animation with the approved frame", async () => {
  const update = vi.spyOn(api, "updateStartingFrame").mockResolvedValue({ ok: true });
  render(<Scene scene={{ ...reviewScene, starting_frame_status: "approved", starting_frame_context: { animation_error: "Animation failed. Your image is saved." } }} manual setUpdated={vi.fn()} />);
  expect(screen.getByRole("alert").textContent).toContain("Animation failed");
  fireEvent.click(screen.getByRole("button", { name: "Retry animation" }));
  await waitFor(() => expect(update).toHaveBeenCalled());
  expect(update.mock.calls[0][1].get("asset_id")).toBe("asset-1");
});

it("remembers a hidden starting-frame panel for that scene after reopening the editor", async () => {
  const { unmount } = render(<Scene scene={reviewScene} manual setUpdated={vi.fn()} />);
  const panel = screen.getByText("Starting frame · Needs review").closest("details");
  expect(panel.open).toBe(true);
  panel.open = false;
  fireEvent(panel, new Event("toggle"));
  await waitFor(() => expect(JSON.parse(localStorage.getItem("editor-workspace:video-1"))["startingFrame:scene-1"]).toBe(false));
  unmount();
  render(<Scene scene={reviewScene} manual setUpdated={vi.fn()} />);
  expect(screen.getByText("Starting frame · Needs review").closest("details").open).toBe(false);
});

it("offers frame preparation without marking the initial description as unsaved", () => {
  render(<Scene scene={{ ...reviewScene, starting_frame: null, starting_asset: null, starting_frame_description: "", scene_image: { file: "/media/old.mp4", prompt: "A teaching lab" } }} manual setUpdated={vi.fn()} />);
  expect(screen.getByText("Starting frame · Not prepared")).toBeTruthy();
  expect(screen.queryByText(/Unsaved changes/)).toBeNull();
  expect(screen.getByRole("button", { name: "Generate starting frame" }).disabled).toBe(false);
});
