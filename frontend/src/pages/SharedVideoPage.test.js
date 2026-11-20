// @vitest-environment happy-dom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { getSharedVideo } from "../api/apiService";
import SharedVideoPage from "./SharedVideoPage";

vi.mock("../api/apiService", () => ({ getSharedVideo: vi.fn() }));
afterEach(cleanup);
beforeEach(() => vi.clearAllMocks());

function showPage() {
  const toggleTheme = vi.fn();
  const view = render(
    <MemoryRouter initialEntries={["/share/secret/"]}>
      <Routes>
        <Route
          path="/share/:token/"
          element={<SharedVideoPage theme="light" toggleTheme={toggleTheme} />}
        />
      </Routes>
    </MemoryRouter>,
  );
  return { ...view, toggleTheme };
}

it("plays a video without auth and displays the saved metadata in the public theme", async () => {
  getSharedVideo.mockResolvedValue({
    ok: true,
    data: {
      title: "Ocean stories",
      description: "Our blue planet\nA little story",
      tags: ["ocean", "#wildlife"],
      media_url: "/api/shared-videos/secret/media/",
    },
  });
  const { container, toggleTheme, unmount } = showPage();
  await screen.findByRole("heading", { name: "Ocean stories" });
  expect(getSharedVideo).toHaveBeenCalledWith(
    "secret",
    expect.any(AbortSignal),
  );
  expect(screen.getByText(/Our blue planet/).textContent).toContain(
    "A little story",
  );
  expect(screen.getByRole("list", { name: "Video tags" }).textContent).toBe(
    "#ocean#wildlife",
  );
  const video = container.querySelector("video");
  expect(video.getAttribute("src")).toBe("/api/shared-videos/secret/media/");
  expect(video.controls).toBe(true);
  expect(video.autoplay).toBe(false);
  await waitFor(() => expect(document.title).toBe("Ocean stories · Viddie"));
  expect(document.querySelector('meta[name="robots"]').content).toBe(
    "noindex, nofollow",
  );
  fireEvent.click(screen.getByRole("button", { name: "Use dark theme" }));
  expect(toggleTheme).toHaveBeenCalledOnce();
  fireEvent.error(video);
  expect(screen.getByRole("alert").textContent).toContain(
    "could not be played",
  );
  unmount();
  expect(document.querySelector('meta[name="robots"]')).toBeNull();
});

it.each([
  [404, "This link wasn’t found"],
  [410, "This link has expired"],
  [429, "Too many requests"],
])(
  "shows the appropriate message for status %s and renders no player",
  async (status, title) => {
    getSharedVideo.mockResolvedValue({ ok: false, status });
    const { container } = showPage();
    await screen.findByRole("heading", { name: title });
    expect(container.querySelector("video")).toBeNull();
    expect(screen.queryByText("Sign in")).toBeNull();
  },
);

it("distinguishes a connection failure from an unavailable video", async () => {
  getSharedVideo.mockResolvedValue({ ok: false, status: null });
  showPage();
  await screen.findByRole("heading", { name: "Unable to load this video" });
  expect(screen.getByText(/Check your connection/)).toBeTruthy();
});
