// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
const { subscribe, stop } = vi.hoisted(() => ({ subscribe: vi.fn(), stop: vi.fn() }));
vi.mock("../api/subscribeUpdates", () => ({ subscribeUpdates: subscribe }));
import { VideoLibraryProgress } from "./VideoLibraryProgress";
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("shows live asset counts, handles unavailable updates, and refreshes on completion", () => {
  let updates;
  subscribe.mockImplementation((path, options) => { updates = options; return stop; });
  const onFinished = vi.fn();
  const view = render(<VideoLibraryProgress video={{ id: "fox", title: "Fox", status: "GENERATION" }} onFinished={onFinished} />);
  expect(screen.getByRole("status").textContent).toBe("Preparing your scenes");
  act(() => updates.onUpdate({ status: "GENERATION", scenes: [{ scene_image: { file: "fox.png" }, narration_status: "available" }, { narration_status: "missing" }] }));
  expect(screen.getByRole("progressbar", { name: "Visuals prepared" }).getAttribute("value")).toBe("1");
  act(() => updates.onError());
  expect(screen.getByText(/Live updates are unavailable/)).toBeTruthy();
  act(() => updates.onUpdate({ status: "READY" }));
  expect(onFinished).toHaveBeenCalledOnce();
  expect(screen.queryByText(/Live updates are unavailable/)).toBeNull();
  view.unmount();
  expect(stop).toHaveBeenCalledOnce();
});
