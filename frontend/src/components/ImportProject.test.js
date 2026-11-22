// @vitest-environment happy-dom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ImportProject } from "./ImportProject";
import { importProject } from "../api/apiService";

vi.mock("../api/apiService", () => ({ importProject: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
const open = () => {
  render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<ImportProject />} />
        <Route path="/videos/copied/" element={<p>Imported editor</p>} />
      </Routes>
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Import project" }));
};
it("uploads a ZIP on confirmation and opens the newly imported project", async () => {
  let complete;
  importProject.mockReturnValue(
    new Promise((resolve) => {
      complete = resolve;
    }),
  );
  open();
  const submit = screen.getByRole("button", { name: "Import project ZIP" });
  expect(submit.disabled).toBe(true);
  const file = new File(["zip"], "project.zip", { type: "application/zip" });
  fireEvent.change(screen.getByLabelText("Project ZIP"), {
    target: { files: [file] },
  });
  expect(importProject).not.toHaveBeenCalled();
  fireEvent.click(submit);
  expect(screen.getByRole("status").textContent).toContain("verifying");
  expect(
    screen.getByRole("button", { name: "Importing project…" }).disabled,
  ).toBe(true);
  expect(importProject.mock.calls[0][0].get("file")).toBe(file);
  complete({ ok: true, data: { id: "copied" } });
  await screen.findByText("Imported editor");
});
it("keeps the dialog and selection available after validation failure", async () => {
  importProject.mockResolvedValue({
    ok: false,
    message: "A project file failed its integrity check.",
  });
  open();
  fireEvent.change(screen.getByLabelText("Project ZIP"), {
    target: { files: [new File(["zip"], "project.zip")] },
  });
  fireEvent.click(screen.getByRole("button", { name: "Import project ZIP" }));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "integrity check",
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Import project ZIP" }).disabled,
    ).toBe(false),
  );
});
it("rejects oversized files without uploading", async () => {
  open();
  const file = new File(["zip"], "huge.zip");
  Object.defineProperty(file, "size", { value: 1024 ** 3 + 1 });
  fireEvent.change(screen.getByLabelText("Project ZIP"), {
    target: { files: [file] },
  });
  fireEvent.click(screen.getByRole("button", { name: "Import project ZIP" }));
  expect((await screen.findByRole("alert")).textContent).toContain("1 GB");
  expect(importProject).not.toHaveBeenCalled();
});
