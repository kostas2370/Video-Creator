// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RenderModal } from "./RenderModal";
import { getVideo, renderVideo } from "../api/apiService";
import { waitForVideo } from "../api/waitForVideo";
vi.mock("../api/apiService", () => ({ getVideo: vi.fn(), renderVideo: vi.fn() }));
vi.mock("../api/waitForVideo", () => ({ waitForVideo: vi.fn() }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("keeps narration review and exports the selected quality and frame rate", async () => {
  getVideo.mockResolvedValue({ ok: true, data: { settings: { export_preset: "DRAFT", export_fps: 24 }, scenes: [{ narration_status: "missing" }] } });
  renderVideo.mockResolvedValue({ ok: true, data: {} });
  waitForVideo.mockReturnValue({ cancel: vi.fn(), promise: Promise.resolve({ outcome: "SETTLED", video: { status: "COMPLETED" } }) });
  const setShowModal = vi.fn();
  render(<RenderModal showModal setShowModal={setShowModal} id="project" name="My video" />);
  expect(screen.getByRole("button", { name: "Export video", exact: true }).disabled).toBe(true);
  await screen.findByText("Missing narration in scene 1");
  expect(screen.getByRole("radio", { name: /Draft/ }).checked).toBe(true);
  fireEvent.click(screen.getByRole("radio", { name: /High/ }));
  fireEvent.change(screen.getByLabelText("Frame rate"), { target: { value: "30" } });
  expect(renderVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Render anyway" }));
  await waitFor(() => expect(renderVideo).toHaveBeenCalledWith("project", { export_preset: "HIGH", export_fps: 30 }));
  expect(setShowModal).toHaveBeenCalledWith(false);
});
