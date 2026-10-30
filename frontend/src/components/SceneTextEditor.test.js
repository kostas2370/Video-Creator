// @vitest-environment happy-dom
import React, { useState } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SceneTextEditor } from "./SceneTextEditor";
const original = { id: "first", text: "Original script" };
function Editor({ scene = original, manual, onSave = async () => false, onRewrite, disabled }) {
  const [draft, setDraft] = useState(null);
  return <SceneTextEditor scene={scene} index={0} manual={manual} disabled={disabled} draft={draft} onDraftChange={(_, next) => setDraft(next)} onSave={onSave} onRewrite={onRewrite} />;
}
afterEach(cleanup);
it("edits directly and saves with Ctrl+Enter", async () => {
  const onSave = vi.fn().mockResolvedValue(true);
  render(<Editor onSave={onSave} />);
  fireEvent.change(screen.getByLabelText("Script for scene 1"), { target: { value: "New script" } });
  fireEvent.keyDown(screen.getByLabelText("Script for scene 1"), { key: "Enter", ctrlKey: true });
  await waitFor(() => expect(onSave).toHaveBeenCalledWith(original, "New script"));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("preserves the draft after a failed save", async () => {
  render(<Editor />);
  fireEvent.change(screen.getByLabelText("Script for scene 1"), { target: { value: "Keep my draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Save text" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Your draft is still here");
  expect(screen.getByLabelText("Script for scene 1").value).toBe("Keep my draft");
});
it("allows clearing manual captions and blocks an empty generated script", async () => {
  const onSave = vi.fn().mockResolvedValue(true);
  const view = render(<Editor onSave={onSave} />);
  fireEvent.change(screen.getByLabelText("Script for scene 1"), { target: { value: "" } });
  expect(screen.getByRole("button", { name: "Save text" }).disabled).toBe(true);
  view.rerender(<Editor manual onSave={onSave} />);
  fireEvent.click(screen.getByRole("button", { name: "Save text" }));
  await waitFor(() => expect(onSave).toHaveBeenCalledWith(original, ""));
});
it("keeps an AI rewrite as a draft until saved", async () => {
  const onSave = vi.fn(), onRewrite = vi.fn().mockResolvedValue("A shorter script");
  render(<Editor onSave={onSave} onRewrite={onRewrite} />);
  fireEvent.click(screen.getByText("Rewrite with AI"));
  fireEvent.change(screen.getByLabelText("Rewrite instructions"), { target: { value: "Make it shorter" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await waitFor(() => expect(screen.getByLabelText("Script for scene 1").value).toBe("A shorter script"));
  expect(onRewrite).toHaveBeenCalledWith(original, "Make it shorter");
  expect(onSave).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Generate rewrite" }).disabled).toBe(true);
});
it("retains edits on a refresh and lets the user resolve conflicting text", () => {
  const view = render(<Editor />);
  fireEvent.change(screen.getByLabelText("Script for scene 1"), { target: { value: "My draft" } });
  view.rerender(<Editor scene={{ ...original, text: "Saved elsewhere" }} />);
  expect(screen.getByLabelText("Script for scene 1").value).toBe("My draft");
  expect(screen.getByRole("alert").textContent).toContain("saved text changed");
  expect(screen.getByRole("button", { name: "Save text" }).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Keep my draft" }));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getByRole("button", { name: "Save text" }).disabled).toBe(false);
});
it("discards with Escape and prevents duplicate pending saves", async () => {
  let finish;
  const onSave = vi.fn(() => new Promise(resolve => { finish = resolve; }));
  render(<Editor onSave={onSave} />);
  const input = screen.getByLabelText("Script for scene 1");
  fireEvent.change(input, { target: { value: "Discard this" } });
  fireEvent.keyDown(input, { key: "Escape" });
  expect(input.value).toBe("Original script");
  fireEvent.change(input, { target: { value: "Save this" } });
  fireEvent.click(screen.getByRole("button", { name: "Save text" }));
  fireEvent.keyDown(input, { key: "Enter", metaKey: true });
  expect(onSave).toHaveBeenCalledOnce();
  expect(input.disabled).toBe(true);
  await act(async () => finish(true));
});
it("locks editing while the project is processing", () => {
  render(<Editor disabled onRewrite={vi.fn()} />);
  expect(screen.getByLabelText("Script for scene 1").disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Save text" }).disabled).toBe(true);
});
