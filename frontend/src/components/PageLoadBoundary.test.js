// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PageLoadBoundary } from "./PageLoadBoundary";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("keeps the mounted page intact when the navigation reset key changes", () => {
  const mounted = vi.fn();
  function Page() {
    React.useEffect(mounted, []);
    return <input aria-label="Draft" defaultValue="" />;
  }
  const view = render(<PageLoadBoundary resetKey="first"><Page /></PageLoadBoundary>);
  fireEvent.change(screen.getByLabelText("Draft"), { target: { value: "Keep this draft" } });
  view.rerender(<PageLoadBoundary resetKey="second"><Page /></PageLoadBoundary>);
  expect(mounted).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("Draft").value).toBe("Keep this draft");
});
it("still recovers from a failed page when navigating elsewhere", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken() { throw new Error("Page download failed"); }
  const view = render(<PageLoadBoundary resetKey="broken"><Broken /></PageLoadBoundary>);
  expect(screen.getByRole("alert").textContent).toContain("could not load");
  view.rerender(<PageLoadBoundary resetKey="working"><p>Working page</p></PageLoadBoundary>);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getByText("Working page")).toBeTruthy();
});
