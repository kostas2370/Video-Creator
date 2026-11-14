// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Link, MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ getVideos: vi.fn() }));
vi.mock("../components/Table", () => ({ DefaultTable: ({ data, view }) => <div data-testid="results" data-view={view}>{data.map(video => <Link key={video.id} to={`/videos/${video.id}/`}>{video.title}</Link>)}</div> }));
import { AuthContext } from "../store/AuthContext";
import { getVideos } from "../api/apiService";
import { Videos } from "./VideosPage";
import { libraryReturnUrl, readLibraryNavigation, saveLibraryNavigation } from "../utils/videoLibraryNavigation";
let scroll;
const response = { data: { count: 30, next: 3, previous: 1, results: [{ id: "fox", title: "Fox project" }] } };
function Position() {
  const location = useLocation();
  const navigate = useNavigate();
  return <><output data-testid="location">{location.pathname}{location.search}</output><button onClick={() => navigate(-1)}>Browser back</button><button onClick={() => navigate(1)}>Browser forward</button></>;
}
function BackToLibrary({ owner }) { return <Link to={libraryReturnUrl(owner)}>All videos</Link>; }
function open(url = "/videos/", owner = "creator", entries) {
  return render(<AuthContext.Provider value={{ user: { id: owner } }}><MemoryRouter initialEntries={entries || [url]}><Position /><Routes><Route path="/videos/" element={<Videos />} /><Route path="/videos/:id/" element={<BackToLibrary owner={owner} />} /></Routes></MemoryRouter></AuthContext.Provider>);
}
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear();
  getVideos.mockResolvedValue(response);
  scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(callback => { callback(0); return 1; });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("restores search, filters, favorites, sort, page, layout and scroll after returning from a project", async () => {
  open("/videos/?search=fox&status=READY&creation_mode=AI&is_favorite=true&ordering=title&view=list&page=2");
  await screen.findByRole("link", { name: "Fox project" });
  expect(screen.getByLabelText("Search videos").value).toBe("fox");
  expect(screen.getByLabelText("Sort videos").value).toBe("title");
  Object.defineProperty(window, "scrollY", { configurable: true, value: 640 });
  fireEvent.scroll(window);
  fireEvent.click(screen.getByRole("link", { name: "Fox project" }));
  const back = await screen.findByRole("link", { name: "All videos" });
  expect(back.getAttribute("href")).toContain("search=fox");
  expect(readLibraryNavigation("creator").scrollY).toBe(640);
  scroll.mockClear();
  fireEvent.click(back);
  await screen.findByRole("link", { name: "Fox project" });
  await waitFor(() => expect(scroll).toHaveBeenCalledWith({ top: 640, left: 0, behavior: "instant" }));
  expect(getVideos).toHaveBeenLastCalledWith("fox", 2, "READY", { creation_mode: "AI", is_favorite: true, ordering: "title" });
  expect(screen.getByTestId("results").getAttribute("data-view")).toBe("list");
  expect(within(screen.getByRole("group", { name: "Video collection" })).getByRole("button", { name: "Favorites" }).getAttribute("aria-pressed")).toBe("true");
  fireEvent.click(screen.getByRole("button", { name: "Grid view" }));
  await waitFor(() => expect(screen.getByTestId("results").getAttribute("data-view")).toBe("grid"));
  expect(screen.getByLabelText("Filter videos by type").value).toBe("AI");
  expect(screen.getByTestId("location").textContent).toContain("status=READY");
});

it("restores a saved library when revisiting its bare URL, after results have loaded", async () => {
  saveLibraryNavigation("creator", { query: "search=fox&view=list&page=2", scrollY: 800 });
  let finish;
  getVideos.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  open();
  expect(screen.getByLabelText("Search videos").value).toBe("fox");
  expect(scroll).not.toHaveBeenCalled();
  await act(async () => finish(response));
  await waitFor(() => expect(scroll).toHaveBeenCalledWith({ top: 800, left: 0, behavior: "instant" }));
  expect(screen.getByTestId("location").textContent).toContain("page=2");
});

it("honors explicit URLs and browser back and forward instead of overwriting them with saved filters", async () => {
  saveLibraryNavigation("creator", { query: "search=saved&view=list", scrollY: 800 });
  open(undefined, "creator", ["/videos/?search=first&status=READY", "/videos/?search=second&status=FAILED"]);
  await screen.findByRole("link", { name: "Fox project" });
  expect(screen.getByLabelText("Search videos").value).toBe("second");
  fireEvent.click(screen.getByRole("button", { name: "Browser back" }));
  await waitFor(() => expect(screen.getByLabelText("Search videos").value).toBe("first"));
  expect(getVideos).toHaveBeenLastCalledWith("first", 1, "READY", expect.any(Object));
  fireEvent.click(screen.getByRole("button", { name: "Browser forward" }));
  await waitFor(() => expect(screen.getByLabelText("Search videos").value).toBe("second"));
  expect(getVideos).toHaveBeenLastCalledWith("second", 1, "FAILED", expect.any(Object));
});

it("resets pagination on status changes and clear filters while retaining the chosen layout", async () => {
  open("/videos/?search=fox&view=list&page=2");
  await screen.findByRole("link", { name: "Fox project" });
  fireEvent.click(within(screen.getByRole("group", { name: "Quick status filters" })).getByRole("button", { name: "Needs attention" }));
  await waitFor(() => expect(getVideos).toHaveBeenLastCalledWith("fox", 1, "FAILED", expect.any(Object)));
  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  await waitFor(() => expect(getVideos).toHaveBeenLastCalledWith("", 1, "", expect.any(Object)));
  expect(screen.getByLabelText("Search videos").value).toBe("");
  expect(screen.getByTestId("results").getAttribute("data-view")).toBe("list");
});

it("does not share saved searches between accounts and works when storage is unavailable", async () => {
  saveLibraryNavigation("someone-else", { query: "search=private", scrollY: 800 });
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("Storage blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("Storage blocked"); });
  open();
  await screen.findByRole("link", { name: "Fox project" });
  expect(screen.getByLabelText("Search videos").value).toBe("");
  fireEvent.click(screen.getByRole("button", { name: "List view" }));
  expect(screen.getByTestId("results").getAttribute("data-view")).toBe("list");
});

it("preserves layout when sort is changed immediately afterwards", async () => {
  open();
  await screen.findByRole("link", { name: "Fox project" });
  act(() => {
    fireEvent.click(screen.getByRole("button", { name: "List view" }));
    fireEvent.change(screen.getByLabelText("Sort videos"), { target: { value: "title" } });
  });
  await waitFor(() => expect(screen.getByTestId("results").getAttribute("data-view")).toBe("list"));
  expect(screen.getByLabelText("Sort videos").value).toBe("title");
  expect(screen.getByTestId("location").textContent).toContain("view=list");
});

it.each([["MANUAL", "Manual edits"], ["STORY", "Story videos"], ["AI", "AI videos"], ["SERIES", "Series episodes"]])("filters %s projects from the visible type selector", async (value, label) => {
  open("/videos/?page=2");
  await screen.findByRole("link", { name: "Fox project" });
  const type = screen.getByRole("combobox", { name: "Filter videos by type" });
  expect(within(type).getByRole("option", { name: label })).toBeTruthy();
  fireEvent.change(type, { target: { value } });
  await waitFor(() => expect(getVideos).toHaveBeenLastCalledWith("", 1, "", expect.objectContaining({ creation_mode: value })));
  expect(screen.getByTestId("location").textContent).toContain(`creation_mode=${value}`);
});


it("explains empty filtered results and resets all constraints while retaining layout", async () => {
  getVideos.mockResolvedValueOnce({ data: { count: 0, results: [] } });
  open("/videos/?search=fox&creation_mode=STORY&status=READY&is_favorite=true&view=list");
  await screen.findByRole("heading", { name: "No videos match your selection" });
  expect(screen.getByText(/We couldn’t find any videos/).textContent).toContain("Story videos");
  fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
  await screen.findByRole("link", { name: "Fox project" });
  expect(getVideos).toHaveBeenLastCalledWith("", 1, "", { creation_mode: undefined, is_favorite: undefined, ordering: "-updated_at" });
  expect(screen.getByTestId("results").getAttribute("data-view")).toBe("list");
});
it("offers a route back to all videos when favorites are empty", async () => {
  getVideos.mockResolvedValueOnce({ data: { count: 0, results: [] } });
  open("/videos/?is_favorite=true");
  await screen.findByRole("heading", { name: "No favorites yet" });
  fireEvent.click(screen.getByRole("button", { name: "Browse all videos" }));
  await screen.findByRole("link", { name: "Fox project" });
  expect(getVideos).toHaveBeenLastCalledWith("", 1, "", expect.objectContaining({ is_favorite: undefined }));
});
