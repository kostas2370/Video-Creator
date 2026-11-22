// @vitest-environment happy-dom
import React from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { RenderModal } from "./RenderModal";
import { getVideo, renderVideo, prepareProjectExport } from "../api/apiService";
import { waitForVideo } from "../api/waitForVideo";
vi.mock("../api/apiService", () => ({
  getVideo: vi.fn(),
  renderVideo: vi.fn(),
  prepareProjectExport: vi.fn(),
}));
vi.mock("../api/waitForVideo", () => ({ waitForVideo: vi.fn() }));
vi.mock("react-toastify", () => ({
  toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() },
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});
it("keeps narration review and exports the selected quality and frame rate", async () => {
  getVideo.mockResolvedValue({
    ok: true,
    data: {
      settings: { export_preset: "DRAFT", export_fps: 24 },
      scenes: [{ narration_status: "missing" }],
    },
  });
  renderVideo.mockResolvedValue({ ok: true, data: {} });
  waitForVideo.mockReturnValue({
    cancel: vi.fn(),
    promise: Promise.resolve({
      outcome: "SETTLED",
      video: { status: "COMPLETED" },
    }),
  });
  const setShowModal = vi.fn();
  render(
    <RenderModal
      showModal
      setShowModal={setShowModal}
      id="project"
      name="My video"
    />,
  );
  expect(
    screen.getByRole("button", { name: "Export video", exact: true }).disabled,
  ).toBe(true);
  await screen.findByText("Missing narration in scene 1");
  expect(screen.getByRole("radio", { name: /Draft/ }).checked).toBe(true);
  fireEvent.click(screen.getByRole("radio", { name: /High/ }));
  fireEvent.change(screen.getByLabelText("Frame rate"), {
    target: { value: "30" },
  });
  expect(renderVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Render anyway" }));
  await waitFor(() =>
    expect(renderVideo).toHaveBeenCalledWith("project", {
      export_preset: "HIGH",
      export_fps: 30,
    }),
  );
  expect(setShowModal).toHaveBeenCalledWith(false);
});

it("offers project ZIP in Export without waiting for narration review", async () => {
  getVideo.mockReturnValue(new Promise(() => {}));
  prepareProjectExport.mockResolvedValue({
    ok: true,
    data: { download_url: "/api/project.zip", filename: "project.zip" },
  });
  const download = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
  render(
    <RenderModal
      showModal
      setShowModal={vi.fn()}
      id="project"
      video={{ id: "project", title: "My project", output: "video.mp4" }}
    />,
  );
  fireEvent.click(screen.getByRole("radio", { name: /Project ZIP/ }));
  expect(screen.queryByLabelText("Frame rate")).toBeNull();
  fireEvent.click(
    screen.getByRole("checkbox", { name: /Include the finished video/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Download project ZIP" }));
  await screen.findByText(/Download started/);
  expect(prepareProjectExport).toHaveBeenCalledWith("project", true);
  expect(download).toHaveBeenCalledOnce();
  expect(renderVideo).not.toHaveBeenCalled();
});

it("defaults drafts to Project ZIP and keeps video rendering unavailable", () => {
  render(
    <RenderModal
      showModal
      setShowModal={vi.fn()}
      id="draft"
      canRender={false}
      video={{ id: "draft", title: "Draft" }}
    />,
  );
  expect(screen.getByRole("radio", { name: /Project ZIP/ }).checked).toBe(true);
  expect(screen.getByRole("radio", { name: /^Video/ }).disabled).toBe(true);
  expect(
    screen.getByRole("button", { name: "Download project ZIP" }).disabled,
  ).toBe(false);
  expect(getVideo).not.toHaveBeenCalled();
});
