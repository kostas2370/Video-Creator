// @vitest-environment happy-dom
import React, { lazy } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DeferredDialog } from "./DeferredDialog";
afterEach(() => { cleanup(); vi.useRealTimers(); });
it("offers recovery when an editor download stays pending without discarding editor changes automatically", async () => {
  vi.useFakeTimers();
  const close = vi.fn();
  const Tool = lazy(() => new Promise(() => {}));
  render(<DeferredDialog open onClose={close}><Tool /></DeferredDialog>);
  expect(screen.getByRole("heading", { name: "Loading editor…" })).toBeTruthy();
  await act(() => vi.advanceTimersByTimeAsync(8000));
  expect(screen.getByRole("heading", { name: "Editor could not finish loading" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Reload page" })).toBeTruthy();
  expect(screen.getByText(/may discard unsaved changes/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Close tool" }));
  expect(close).toHaveBeenCalledOnce();
});

it("keeps the surrounding editor available when a tool chunk fails", async () => {
  const error = vi.spyOn(console, "error").mockImplementation(() => {});
  const Tool = lazy(() => Promise.reject(new Error("Failed to fetch dynamically imported module")));
  try {
    await act(async () => render(<><p>Saved project</p><DeferredDialog open onClose={vi.fn()}><Tool /></DeferredDialog></>));
    expect(screen.getByText("Saved project")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Editor could not finish loading" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Close tool" })).toBeTruthy();
  } finally { error.mockRestore(); }
});
