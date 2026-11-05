// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { getIcons, uploadIcon, updateIcon, deleteIcon } from "../api/apiService";
import { IconAssets } from "./IconAssets";

vi.mock("../api/apiService", () => ({ getIcons: vi.fn(), uploadIcon: vi.fn(), updateIcon: vi.fn(), deleteIcon: vi.fn() }));
const shared = { key: "lucide:bank", name: "Bank", collection: "lucide", file: "/bank.svg", description: "Bank building", license: "ISC", license_url: "https://lucide.dev/license", attribution: "Lucide", is_owner: false };
const own = { ...shared, key: "custom:engine", name: "My engine", collection: "custom", is_owner: true };
const reply = (results = [shared, own], extra = {}) => ({ ok: true, data: { results, count: results.length, current: 1, next: null, previous: null, ...extra } });
beforeEach(() => { getIcons.mockResolvedValue(reply()); });
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it("previews shared icons with license details and no management controls", async () => {
  render(<IconAssets />);
  fireEvent.click(await screen.findByRole("button", { name: "Bank (lucide)" }));
  expect(screen.getByRole("img", { name: "Bank" }).getAttribute("src")).toBe(shared.file);
  expect(screen.getByRole("link", { name: "ISC" }).getAttribute("href")).toBe(shared.license_url);
  expect(screen.queryByRole("button", { name: "Delete icon" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Save changes" })).toBeNull();
});

it("filters personal icons and searches the same catalog used by diagrams", async () => {
  render(<IconAssets />);
  await screen.findByRole("button", { name: "My engine (custom)" });
  fireEvent.click(screen.getByLabelText("My icons"));
  fireEvent.change(screen.getByLabelText("Search icons"), { target: { value: "engine" } });
  await waitFor(() => expect(getIcons).toHaveBeenLastCalledWith({ search: "engine", page: 1, mine: true }));
});

it("uploads to the library and opens the new icon without requiring a diagram", async () => {
  uploadIcon.mockResolvedValue({ ok: true, data: own });
  render(<IconAssets />);
  fireEvent.click(screen.getByText("Upload your own icon"));
  fireEvent.change(screen.getByLabelText("Icon name"), { target: { value: "My engine" } });
  const file = new File(["image"], "engine.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText("Icon file"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload icon" }));
  expect(await screen.findByRole("dialog", { name: "My engine" })).toBeTruthy();
  expect(uploadIcon.mock.calls[0][0].get("file")).toBe(file);
  fireEvent.click(screen.getByRole("button", { name: "Close editor" }));
  expect(screen.getByLabelText("Icon name").value).toBe("");
});

it("keeps a failed rename for retry and refreshes the catalog after saving", async () => {
  updateIcon.mockResolvedValueOnce({ ok: false, message: "Try later" }).mockResolvedValue({ ok: true });
  render(<IconAssets />);
  fireEvent.click(await screen.findByRole("button", { name: "My engine (custom)" }));
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText("Icon name"), { target: { value: "New engine" } });
  fireEvent.change(dialog.getByLabelText("Description"), { target: { value: "My car engine" } });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Try later");
  expect(dialog.getByLabelText("Icon name").value).toBe("New engine");
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(updateIcon).toHaveBeenLastCalledWith(own.key, { name: "New engine", description: "My car engine" });
  expect(getIcons.mock.calls.length).toBeGreaterThan(1);
});

it("confirms deletion, retains failures, and refreshes after a successful retry", async () => {
  deleteIcon.mockResolvedValueOnce({ ok: false, message: "Delete failed" }).mockResolvedValue({ ok: true });
  render(<IconAssets />);
  fireEvent.click(await screen.findByRole("button", { name: "My engine (custom)" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete icon" }));
  expect(screen.getByText(/Already exported videos stay unchanged/)).toBeTruthy();
  expect(deleteIcon).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  expect((await screen.findByRole("alert")).textContent).toContain("Delete failed");
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(deleteIcon).toHaveBeenLastCalledWith(own.key);
});

it("returns to an available page when deleting the last icon on the final page", async () => {
  getIcons.mockResolvedValueOnce(reply([shared], { next: 2, count: 25 }))
    .mockResolvedValueOnce(reply([own], { current: 2, previous: 1, count: 25 }))
    .mockResolvedValueOnce({ ok: false, status: 404 })
    .mockResolvedValue(reply([shared]));
  deleteIcon.mockResolvedValue({ ok: true });
  render(<IconAssets />);
  fireEvent.click(await screen.findByRole("button", { name: "Next" }));
  fireEvent.click(await screen.findByRole("button", { name: "My engine (custom)" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete icon" }));
  fireEvent.click(screen.getByRole("button", { name: "Delete", exact: true }));
  await screen.findByRole("button", { name: "Bank (lucide)" });
  expect(getIcons).toHaveBeenLastCalledWith({ search: "", page: 1 });
});
