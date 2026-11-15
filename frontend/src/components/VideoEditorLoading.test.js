// @vitest-environment happy-dom
import React, { lazy, Suspense } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { VideoEditorEntry, VideoEditorLoading } from "./VideoEditorLoading";
import { isVideoEditorPath } from "../utils/pageLayout";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("opens an editor at the top before its route chunk loads without scrolling again on data updates", async () => {
  const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  let finish;
  const Editor = lazy(() => new Promise(resolve => { finish = resolve; }));
  function Pages() {
    const location = useLocation();
    return <><VideoEditorEntry /><Suspense fallback={isVideoEditorPath(location.pathname) ? <VideoEditorLoading /> : null}><Routes>
      <Route path="/videos/" element={<Link to="/videos/fox/">Open fox</Link>} />
      <Route path="/videos/:id/" element={<Suspense fallback={<VideoEditorLoading />}><Editor /></Suspense>} />
    </Routes></Suspense></>;
  }
  const view = render(<MemoryRouter initialEntries={["/videos/"]}><Pages /></MemoryRouter>);
  expect(scroll).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("link", { name: "Open fox" }));
  expect((await screen.findByRole("status")).textContent).toBe("Loading video editor…");
  expect(screen.getByRole("main", { name: "Loading video editor" }).getAttribute("aria-busy")).toBe("true");
  expect(scroll).toHaveBeenCalledExactlyOnceWith({ top: 0, left: 0, behavior: "instant" });
  await act(async () => finish({ default: () => <h1>Fox editor</h1> }));
  expect(screen.getByRole("heading", { name: "Fox editor" })).toBeTruthy();
  expect(scroll).toHaveBeenCalledTimes(1);
  view.rerender(<MemoryRouter initialEntries={["/videos/"]}><Pages /></MemoryRouter>);
  expect(scroll).toHaveBeenCalledTimes(1);
});
