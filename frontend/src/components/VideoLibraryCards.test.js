// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", async original => ({ ...await original(), toggleVideoFavorite: vi.fn() }));
import { toggleVideoFavorite } from "../api/apiService";
import { DefaultTable } from "./Table";
const project = { id: "fox", title: "Fox story", status: "READY", is_favorite: false };
function Library({ view }) {
  const [videos, setVideos] = useState([project]);
  return <MemoryRouter><DefaultTable data={videos} setVideos={setVideos} view={view} /></MemoryRouter>;
}
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it.each(["grid", "list"])("keeps favorites and editor links usable in the %s layout", async view => {
  toggleVideoFavorite.mockResolvedValue({ ok: true, data: { is_favorite: true } });
  render(<Library view={view} />);
  expect(screen.getByRole("link", { name: "Open editor for Fox story" }).getAttribute("href")).toBe("/videos/fox/");
  const favorite = screen.getByRole("button", { name: "Add Fox story to favorites" });
  expect(favorite.closest("a")).toBeNull();
  fireEvent.click(favorite);
  await waitFor(() => expect(screen.getByRole("button", { name: "Remove Fox story from favorites" }).getAttribute("aria-pressed")).toBe("true"));
  expect(toggleVideoFavorite).toHaveBeenCalledOnce();
  expect(toggleVideoFavorite).toHaveBeenCalledWith("fox");
});
