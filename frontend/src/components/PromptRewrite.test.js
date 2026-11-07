// @vitest-environment happy-dom
import React, { useState } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PromptRewrite } from "./PromptRewrite";
import { CreationDraftContext, useCreationDraft } from "../hooks/useCreationDraft";
import AuthContext from "../store/AuthContext";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });
const open = () => fireEvent.click(screen.getByText("Rewrite with AI"));
function Editor({ kind = "video" }) {
  const [value, setValue] = useState("Milo finds a lantern");
  return <><textarea aria-label="Original prompt" value={value} onChange={event => setValue(event.target.value)} /><PromptRewrite kind={kind} value={value} onUse={setValue} /></>;
}

it("previews a rewrite before applying it to the editable prompt", async () => {
  const request = vi.spyOn(api, "rewritePrompt").mockResolvedValue({ ok: true, data: { prompt: "Milo discovers a glowing lantern at dusk." } });
  render(<Editor />);
  open();
  fireEvent.change(screen.getByLabelText(/What would you like to change/), { target: { value: "More visual" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await screen.findByText("Suggested rewrite");
  expect(screen.getByLabelText("Original prompt").value).toBe("Milo finds a lantern");
  expect(request).toHaveBeenCalledWith({ kind: "video", prompt: "Milo finds a lantern", instructions: "More visual" });
  fireEvent.click(screen.getByRole("button", { name: "Use rewrite" }));
  expect(screen.getByLabelText("Original prompt").value).toBe("Milo discovers a glowing lantern at dusk.");
});

it("blocks a late rewrite after the user edits the source", async () => {
  let finish;
  vi.spyOn(api, "rewritePrompt").mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<Editor kind="visual" />);
  open();
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  expect(screen.getByRole("button", { name: "Rewriting…" }).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Original prompt"), { target: { value: "Milo enters a cave" } });
  await act(async () => finish({ ok: true, data: { prompt: "An old rewritten idea" } }));
  expect(screen.getByRole("button", { name: "Use rewrite" }).disabled).toBe(true);
  expect(screen.getByLabelText("Original prompt").value).toBe("Milo enters a cave");
  expect(screen.getByRole("status").textContent).toContain("prompt changed");
});

it("discards suggestions and reports failures without altering the original", async () => {
  const request = vi.spyOn(api, "rewritePrompt").mockResolvedValueOnce({ ok: true, data: { prompt: "A different wording" } }).mockResolvedValueOnce({ ok: false, message: "Provider unavailable" });
  render(<Editor />);
  open();
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await screen.findByText("Suggested rewrite");
  fireEvent.click(screen.getByRole("button", { name: "Discard rewrite" }));
  expect(screen.queryByText("Suggested rewrite")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Provider unavailable"));
  expect(request).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText("Original prompt").value).toBe("Milo finds a lantern");
});

it("requires a nonempty prompt and honors disabled controls", () => {
  const request = vi.spyOn(api, "rewritePrompt");
  const { rerender } = render(<PromptRewrite kind="series" value="" onUse={vi.fn()} />);
  open();
  expect(screen.getByRole("button", { name: "Generate rewrite" }).disabled).toBe(true);
  rerender(<PromptRewrite kind="series" value="A series premise" disabled onUse={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Generate rewrite" }).disabled).toBe(true);
  expect(request).not.toHaveBeenCalled();
});

function SavedEditor() {
  const draft = useCreationDraft("rewrite-test", { ui: {} }, saved => saved);
  return <CreationDraftContext.Provider value={draft}><PromptRewrite kind="series" value="Weekly fox mysteries" onUse={vi.fn()} /></CreationDraftContext.Provider>;
}
it("recovers an unaccepted rewrite after reopening without another paid call", async () => {
  const request = vi.spyOn(api, "rewritePrompt").mockResolvedValue({ ok: true, data: { prompt: "A recurring fox detective solves new mysteries." } });
  const wrap = () => <AuthContext.Provider value={{ user: { id: "alice" } }}><SavedEditor /></AuthContext.Provider>;
  const first = render(wrap());
  open();
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await screen.findByText("Suggested rewrite");
  first.unmount();
  render(wrap());
  expect(screen.getByText("Suggested rewrite")).toBeTruthy();
  expect(request).toHaveBeenCalledOnce();
});
