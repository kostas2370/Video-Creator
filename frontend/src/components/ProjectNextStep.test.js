// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ProjectNextStep } from "./ProjectNextStep";
import { projectNextStep } from "../utils/projectNextStep";
const scene = { id: "first", scene_image: { file: "/scene.jpg" }, narration_status: "available" };
const video = { status: "READY", video_type: "AI", scenes: [scene] };
afterEach(cleanup);
it.each([
  [{ ...video, status: "REVIEW" }, "review"],
  [video, "export"],
  [{ ...video, status: "FAILED", video_type: "MANUAL" }, "scene"],
  [{ ...video, status: "COMPLETED", output: "/export.mp4" }, "watch"],
  [{ ...video, status: "FAILED", render_error: { message: "Failed" } }, "export"],
  [{ ...video, status: "FAILED" }, "resume"],
  [{ ...video, can_retry_narration: true }, "settings"],
  [{ ...video, scenes: [] }, "add"],
  [{ ...video, scenes: [{ ...scene, narration_status: "missing" }] }, "scene"],
  [{ ...video, scenes: [{ ...scene, starting_frame_required: true, scene_image: null }] }, "scene"],
])("routes project state to the appropriate next action (%j)", (project, action) => {
  expect(projectNextStep(project).action).toBe(action);
});
it.each(["GENERATION", "RENDERING"])("shows progress without offering another operation during %s", status => {
  render(<ProjectNextStep video={{ ...video, status }} onAction={vi.fn()} />);
  expect(screen.getByText("In progress")).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
it("opens the existing workflow rather than starting generation directly", () => {
  const onAction = vi.fn();
  render(<ProjectNextStep video={{ ...video, status: "FAILED" }} onAction={onAction} />);
  fireEvent.click(screen.getByRole("button", { name: "Generate missing scenes" }));
  expect(onAction).toHaveBeenCalledWith(expect.objectContaining({ action: "resume" }));
});
it("blocks export until edits are saved and the project is renderable", () => {
  const onAction = vi.fn();
  const view = render(<ProjectNextStep video={video} disabled canExport onAction={onAction} />);
  fireEvent.click(screen.getByRole("button", { name: "Export current edit" }));
  expect(onAction).not.toHaveBeenCalled();
  view.rerender(<ProjectNextStep video={video} canExport={false} onAction={onAction} />);
  expect(screen.getByRole("button").disabled).toBe(true);
  view.rerender(<ProjectNextStep video={video} canExport onAction={onAction} />);
  fireEvent.click(screen.getByRole("button"));
  expect(onAction).toHaveBeenCalledOnce();
});
