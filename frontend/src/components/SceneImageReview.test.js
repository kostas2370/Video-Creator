// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SceneStartingImage } from "./SceneStartingImage";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

const scene = {
  id: "scene-1", video: "video-1", starting_image_required: true,
  starting_asset: "asset-1", starting_image: "/media/start.png",
  starting_image_description: "Milo at gate", starting_image_status: "needs_review",
  starting_image_review_key: "source-1",
};
const review = {
  source_key: "source-1", verdict: "needs_changes", summary: "The scarf differs.",
  findings: [{ category: "character", issue: "The scarf is red.", fix: "Use green." }],
  suggested_description: "Milo at gate wearing a green scarf",
};

it("reviews the saved image and lets the user use corrections without generating or approving", async () => {
  const request = vi.spyOn(api, "reviewStartingImage").mockResolvedValue({ ok: true, data: review });
  const generate = vi.spyOn(api, "generateSceneImage");
  const update = vi.spyOn(api, "updateStartingImage");
  const saved = vi.fn();
  render(<SceneStartingImage scene={scene} index={0} onSaved={saved} />);
  fireEvent.click(screen.getByRole("button", { name: "Review image with AI" }));
  await screen.findByText("Changes suggested");
  expect(request).toHaveBeenCalledWith("scene-1", "asset-1");
  expect(screen.getByText("Review details").closest("details").open).toBe(false);
  fireEvent.click(screen.getByText("Review details"));
  expect(screen.getByText("The scarf is red.")).toBeTruthy();
  expect(saved).toHaveBeenCalledWith(true);
  fireEvent.click(screen.getByRole("button", { name: "Use suggested description" }));
  expect(screen.getByRole("textbox", { name: "Scene 1 starting image description" }).value).toBe(review.suggested_description);
  expect(screen.getByText("Change image · Unsaved changes").closest("details").open).toBe(true);
  expect(screen.getByRole("button", { name: "Review image with AI" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Approve starting image" }).disabled).toBe(true);
  expect(generate).not.toHaveBeenCalled();
  expect(update).not.toHaveBeenCalled();
});

it("shows saved reviews after reopening and disables review for uploaded replacements", () => {
  render(<SceneStartingImage scene={{ ...scene, starting_image_review: review }} index={0} onSaved={vi.fn()} />);
  expect(screen.getByText("Changes suggested")).toBeTruthy();
  fireEvent.click(screen.getByText("Change image"));
  fireEvent.click(screen.getByText("Upload an image instead"));
  fireEvent.change(screen.getByLabelText("Scene 1 replacement starting image"), {
    target: { files: [new File(["image"], "replacement.png", { type: "image/png" })] },
  });
  expect(screen.getByRole("button", { name: "Review again with AI" }).disabled).toBe(true);
});

it("prevents duplicate review requests and leaves approval available after review finishes", async () => {
  let finish;
  const request = vi.spyOn(api, "reviewStartingImage").mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<SceneStartingImage scene={scene} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review image with AI" }));
  const pending = screen.getByRole("button", { name: "Reviewing image…" });
  expect(pending.disabled).toBe(true);
  fireEvent.click(pending);
  expect(request).toHaveBeenCalledTimes(1);
  finish({ ok: true, data: { ...review, verdict: "ready", findings: [], suggested_description: "" } });
  await screen.findByText("Looks ready");
  expect(screen.getByRole("button", { name: "Approve starting image" }).disabled).toBe(false);
  expect(screen.queryByRole("button", { name: "Animate approved image" })).toBeNull();
});

it("reports review failures and keeps the previous review", async () => {
  vi.spyOn(api, "reviewStartingImage").mockResolvedValue({ ok: false, message: "The model could not read the image" });
  render(<SceneStartingImage scene={{ ...scene, starting_image_review: review }} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review again with AI" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("could not read"));
  expect(screen.getByText("Changes suggested")).toBeTruthy();
});

it("discards a review when its source has changed", async () => {
  vi.spyOn(api, "reviewStartingImage").mockResolvedValue({ ok: true, data: { ...review, source_key: "old-source" } });
  render(<SceneStartingImage scene={scene} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Review image with AI" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("changed"));
  expect(screen.queryByText("Changes suggested")).toBeNull();
});

it("hides a previous review when the server reports changed scene inputs", () => {
  const { rerender } = render(<SceneStartingImage scene={{ ...scene, starting_image_review: review }} index={0} onSaved={vi.fn()} />);
  expect(screen.getByText("Changes suggested")).toBeTruthy();
  rerender(<SceneStartingImage scene={{ ...scene, starting_image_review_key: "new-source", starting_image_review: null }} index={0} onSaved={vi.fn()} />);
  expect(screen.queryByText("Changes suggested")).toBeNull();
});
