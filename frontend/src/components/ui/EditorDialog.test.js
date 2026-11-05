// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { EditorDialog } from "./EditorDialog";
import { ConfirmationDialog } from "./ConfirmationDialog";
import { SaveTemplateModal } from "../SaveTemplateModal";
import { createTemplate } from "../../api/apiService";
vi.mock("../../api/apiService", () => ({ createTemplate: vi.fn() }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("blocks dismissal while saving and restores Escape dismissal afterward", async () => {
  const onClose = vi.fn();
  const view = render(<EditorDialog open onClose={onClose} title="Settings" busy><input aria-label="Name" /></EditorDialog>);
  const user = userEvent.setup();
  expect(screen.getByRole("button", { name: "Close editor" }).disabled).toBe(true);
  await user.keyboard("{Escape}");
  expect(onClose).not.toHaveBeenCalled();
  view.rerender(<EditorDialog open onClose={onClose} title="Settings"><input aria-label="Name" /></EditorDialog>);
  await user.keyboard("{Escape}");
  await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
});
it("requires explicit confirmation, preserves errors and supports a retry", async () => {
  const onConfirm = vi.fn().mockResolvedValueOnce({ ok: false, message: "Please retry" }).mockResolvedValueOnce({ ok: true });
  const onClose = vi.fn();
  render(<ConfirmationDialog open onClose={onClose} onConfirm={onConfirm} title="Remove item?" confirmLabel="Remove" />);
  expect(onConfirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Remove", exact: true }));
  expect((await screen.findByRole("alert")).textContent).toBe("Please retry");
  expect(onClose).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Remove", exact: true }));
  await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
});
it("submits template settings from the fixed footer and prevents duplicate requests", async () => {
  let finish;
  createTemplate.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const setShowModal = vi.fn();
  render(<SaveTemplateModal showModal setShowModal={setShowModal} settings={{ video_format: "PORTRAIT" }} />);
  fireEvent.change(screen.getByLabelText("Template name"), { target: { value: "  My setup  " } });
  fireEvent.click(screen.getByRole("button", { name: "Save template" }));
  await waitFor(() => expect(createTemplate).toHaveBeenCalledWith({ video_format: "PORTRAIT", title: "My setup" }));
  expect(screen.getByRole("button", { name: "Saving…" }).disabled).toBe(true);
  expect(setShowModal).not.toHaveBeenCalled();
  finish({ ok: true, data: { title: "My setup" } });
  await waitFor(() => expect(setShowModal).toHaveBeenCalledWith(false));
  expect(createTemplate).toHaveBeenCalledTimes(1);
});
