// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ deleteDraftVideo: vi.fn() }));
import { deleteDraftVideo } from "../api/apiService";
import { DeleteDraftProject } from "./DeleteDraftProject";

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
const mount = onDeleted => render(<MemoryRouter><DeleteDraftProject id="draft" onDeleted={onDeleted} /></MemoryRouter>);

it("requires confirmation and cancellation preserves the project", async () => {
  mount(vi.fn());
  fireEvent.click(screen.getByRole("button", { name: "Delete draft project" }));
  expect(screen.getByRole("heading", { name: "Delete draft project?" })).toBeTruthy();
  expect(deleteDraftVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(deleteDraftVideo).not.toHaveBeenCalled();
});

it("clears the saved project reference only after successful deletion", async () => {
  deleteDraftVideo.mockResolvedValue({ ok: true, status: 204 });
  const deleted = vi.fn(); mount(deleted);
  fireEvent.click(screen.getByRole("button", { name: "Delete draft project" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  await waitFor(() => expect(deleted).toHaveBeenCalledOnce());
  expect(deleteDraftVideo).toHaveBeenCalledWith("draft");
});

it("preserves the draft when generation has started or deletion fails", async () => {
  deleteDraftVideo.mockResolvedValue({ ok: false, status: 409, message: "This project is still processing." });
  const deleted = vi.fn(); mount(deleted);
  fireEvent.click(screen.getByRole("button", { name: "Delete draft project" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toContain("still processing");
  expect(deleted).not.toHaveBeenCalled();
});

it("clears a stale browser reference when the project was already deleted", async () => {
  deleteDraftVideo.mockResolvedValue({ ok: false, status: 404 });
  const deleted = vi.fn(); mount(deleted);
  fireEvent.click(screen.getByRole("button", { name: "Delete draft project" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  await waitFor(() => expect(deleted).toHaveBeenCalledOnce());
});
