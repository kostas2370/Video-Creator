// @vitest-environment happy-dom
import React, { useState } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StoryboardRevision } from "./StoryboardRevision";
import * as api from "../api/apiService";

const original = { title: "Original", scenes: [{ scene: "Opening", sentences: [{ sentence: "Original narration", image_description: "A street" }] }] };
const revised = { ...original, title: "Suspenseful revision" };
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function Editor() {
  const [storyboard, setStoryboard] = useState(original);
  return <>
    <input aria-label="Current title" value={storyboard.title} onChange={event => setStoryboard({ ...storyboard, title: event.target.value })} />
    <StoryboardRevision videoId="video-1" storyboard={storyboard} onApply={setStoryboard} />
  </>;
}
const request = () => {
  fireEvent.change(screen.getByLabelText("What would you like to change?"), { target: { value: "More suspense" } });
  fireEvent.click(screen.getByRole("button", { name: "Suggest revision" }));
};
it("previews without changing the original and supports follow-up revisions after applying", async () => {
  const revise = vi.spyOn(api, "reviseStoryboard").mockResolvedValue({ ok: true, data: revised });
  render(<Editor />);
  request();
  await screen.findByText("Suspenseful revision");
  expect(screen.getByLabelText("Current title").value).toBe("Original");
  expect(revise).toHaveBeenCalledWith("video-1", { storyboard: original, instructions: "More suspense" });
  fireEvent.click(screen.getByRole("button", { name: "Apply revision" }));
  expect(screen.getByLabelText("Current title").value).toBe("Suspenseful revision");
  request();
  await screen.findByRole("button", { name: "Apply revision" });
  expect(revise.mock.calls[1][1].storyboard.title).toBe("Suspenseful revision");
  fireEvent.click(screen.getByRole("button", { name: "Discard revision" }));
  expect(screen.queryByRole("button", { name: "Apply revision" })).toBeNull();
});
it("blocks stale proposals when edits happen during a request and prevents duplicate requests", async () => {
  let finish;
  const revise = vi.spyOn(api, "reviseStoryboard").mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<Editor />);
  request();
  expect(screen.getByRole("button", { name: "Revising storyboard…" }).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Current title"), { target: { value: "My newer edit" } });
  await act(async () => finish({ ok: true, data: revised }));
  expect(screen.getByRole("button", { name: "Apply revision" }).disabled).toBe(true);
  expect(screen.getByRole("status").textContent).toContain("storyboard changed");
  expect(revise).toHaveBeenCalledOnce();
});
it("reports failures without altering the current storyboard", async () => {
  vi.spyOn(api, "reviseStoryboard").mockResolvedValue({ ok: false, message: "Provider unavailable" });
  render(<Editor />);
  request();
  expect((await screen.findByRole("alert")).textContent).toBe("Provider unavailable");
  expect(screen.getByLabelText("Current title").value).toBe("Original");
});

it("recovers from a network failure and keeps the existing proposal available", async () => {
  const revise = vi.spyOn(api, "reviseStoryboard")
    .mockResolvedValueOnce({ ok: true, data: revised })
    .mockRejectedValueOnce(new Error("Network unavailable"))
    .mockResolvedValueOnce({ ok: true, data: revised });
  render(<Editor />);
  request();
  await screen.findByText("Suspenseful revision");
  request();
  expect((await screen.findByRole("alert")).textContent).toBe("Could not revise the storyboard. Please try again.");
  expect(screen.getByRole("button", { name: "Apply revision" }).disabled).toBe(false);
  expect(screen.getByLabelText("Current title").value).toBe("Original");
  request();
  await screen.findByRole("button", { name: "Suggest revision" });
  expect(screen.queryByRole("alert")).toBeNull();
  expect(revise).toHaveBeenCalledTimes(3);
});
