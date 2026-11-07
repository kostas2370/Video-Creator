// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SceneStartingFrame } from "./SceneStartingFrame";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

const scene = {
  id: "scene-1", video: "video-1", starting_frame_required: true,
  starting_asset: "asset-1", starting_frame: "/media/start.png",
  starting_frame_description: "Milo at gate", starting_frame_status: "needs_review",
  starting_frame_review_key: "source-1",
};
const review = {
  source_key: "source-1", verdict: "needs_changes", summary: "The scarf differs.",
  findings: [{ category: "character", issue: "The scarf is red.", fix: "Use green." }],
  suggested_description: "Milo at gate wearing a green scarf",
};

it("reviews the saved frame and lets the user use corrections without generating or approving", async () => {
  const request = vi.spyOn(api, "reviewStartingFrame").mockResolvedValue({ ok: true, data: review });
  const generate = vi.spyOn(api, "generateSceneImage");
  const update = vi.spyOn(api, "updateStartingFrame");
  const saved = vi.fn();
  render(<SceneStartingFrame scene={scene} index={0} onSaved={saved} />);
  fireEvent.click(screen.getByRole("button", { name: "Review frame with AI" }));
  await screen.findByText("Changes suggested");
  expect(request).toHaveBeenCalledWith("scene-1", "asset-1");
  expect(screen.getByText("Review details").closest("details").open).toBe(false);
  fireEvent.click(screen.getByText("Review details"));
  expect(screen.getByText("The scarf is red.")).toBeTruthy();
  expect(saved).toHaveBeenCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "Use suggested description" }));
  expect(screen.getByRole("textbox", { name: "Scene 1 starting frame description" }).value).toBe(review.suggested_description);
  expect(screen.getByText("Change frame · Unsaved changes").closest("details").open).toBe(true);
  expect(screen.getByRole("button", { name: "Review frame with AI" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Approve starting frame" }).disabled).toBe(true);
  expect(generate).not.toHaveBeenCalled();
  expect(update).not.toHaveBeenCalled();
});

it("shows saved reviews after reopening and disables review for uploaded replacements", () => {
  render(<SceneStartingFrame scene={{ ...scene, starting_frame_review: review }} index={0} onSaved={vi.fn()} />);
  expect(screen.getByText("Changes suggested")).toBeTruthy();
  fireEvent.click(screen.getByText("Change frame"));
  fireEvent.click(screen.getByText("Upload a frame instead"));
  fireEvent.change(screen.getByLabelText("Scene 1 replacement starting frame"), {
    target: { files: [new File(["image"], "replacement.png", { type: "image/png" })] },
  });
  expect(screen.getByRole("button", { name: "Review frame again with AI" }).disabled).toBe(true);
});

it("prevents duplicate review requests and leaves approval available after review finishes", async () => {
  let finish;
  const request = vi.spyOn(api, "reviewStartingFrame").mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<SceneStartingFrame scene={scene} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review frame with AI" }));
  const pending = screen.getByRole("button", { name: "Reviewing frame…" });
  expect(pending.disabled).toBe(true);
  fireEvent.click(pending);
  expect(request).toHaveBeenCalledTimes(1);
  finish({ ok: true, data: { ...review, verdict: "ready", findings: [], suggested_description: "" } });
  await screen.findByText("Looks ready");
  expect(screen.getByRole("button", { name: "Approve starting frame" }).disabled).toBe(false);
  expect(screen.queryByRole("button", { name: "Animate approved frame" })).toBeNull();
});

it("reports review failures and keeps the previous review", async () => {
  vi.spyOn(api, "reviewStartingFrame").mockResolvedValue({ ok: false, message: "The model could not read the image" });
  render(<SceneStartingFrame scene={{ ...scene, starting_frame_review: review }} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review frame again with AI" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("could not read"));
  expect(screen.getByText("Changes suggested")).toBeTruthy();
});

it("discards a review when its source has changed", async () => {
  vi.spyOn(api, "reviewStartingFrame").mockResolvedValue({ ok: true, data: { ...review, source_key: "old-source" } });
  render(<SceneStartingFrame scene={scene} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review frame with AI" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("changed"));
  expect(screen.queryByText("Changes suggested")).toBeNull();
});

it("hides a previous review when the server reports changed scene inputs", () => {
  const { rerender } = render(<SceneStartingFrame scene={{ ...scene, starting_frame_review: review }} index={0} onSaved={vi.fn()} />);
  expect(screen.getByText("Changes suggested")).toBeTruthy();
  rerender(<SceneStartingFrame scene={{ ...scene, starting_frame_review_key: "new-source", starting_frame_review: null }} index={0} onSaved={vi.fn()} />);
  expect(screen.queryByText("Changes suggested")).toBeNull();
});
