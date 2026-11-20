// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { prepareProjectExport } from "../api/apiService";
import { ExportProject } from "./ExportProject";

vi.mock("../api/apiService", () => ({ prepareProjectExport: vi.fn() }));
const video = {
  id: "project-1",
  title: "Portable story",
  output: "/media/output.mp4",
};
beforeEach(() => vi.clearAllMocks());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("preflights on an explicit click and starts a native download with the selected output option", async () => {
  prepareProjectExport.mockResolvedValue({
    ok: true,
    data: {
      download_url:
        "http://localhost/api/videos/project-1/export-project/?include_output=true",
      filename: "portable-story-project.zip",
    },
  });
  let clicked;
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
    function () {
      clicked = { href: this.href, download: this.download };
    },
  );
  render(<ExportProject video={video} />);
  expect(prepareProjectExport).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("checkbox", { name: /Include the finished video/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Download project ZIP" }));
  await screen.findByRole("status");
  expect(prepareProjectExport).toHaveBeenCalledWith("project-1", true);
  expect(clicked).toEqual({
    href: "http://localhost/api/videos/project-1/export-project/?include_output=true",
    download: "portable-story-project.zip",
  });
  expect(screen.getByRole("status").textContent).toContain("Download started");
});

it("shows preflight errors without starting an incomplete download", async () => {
  prepareProjectExport.mockResolvedValue({
    ok: false,
    message: "Some project media is missing.",
  });
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
  render(<ExportProject video={video} />);
  fireEvent.click(screen.getByRole("button", { name: "Download project ZIP" }));
  expect((await screen.findByRole("alert")).textContent).toContain("missing");
  expect(prepareProjectExport).toHaveBeenCalledWith("project-1", false);
  expect(click).not.toHaveBeenCalled();
});

it("allows draft exports while disabling the absent finished video", () => {
  render(<ExportProject video={{ id: "draft", title: "Draft" }} />);
  expect(screen.getByRole("checkbox").disabled).toBe(true);
  expect(
    screen.getByRole("button", { name: "Download project ZIP" }).disabled,
  ).toBe(false);
});
