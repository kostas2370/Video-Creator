// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Avatar } from "./AvatarPage";
import { Videos } from "./VideosPage";
import { Usage } from "./UsagePage";
import { getAvatars, getVideos, getUsage } from "../api/apiService";
vi.mock("../api/apiService", () => ({ getAvatars: vi.fn(), getVideos: vi.fn(), getUsage: vi.fn() }));
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => {} }));
vi.mock("../components/AvatarCreationModal", () => ({ AvatarCreationModal: () => null }));
vi.mock("../components/ui/AvatarCards", () => ({ Card: ({ title }) => <article>{title}</article> }));
vi.mock("../components/Table", () => ({ DefaultTable: ({ data }) => <div>{data.map(item => <article key={item.id}>{item.title}</article>)}</div> }));
beforeEach(() => { vi.useFakeTimers(); vi.clearAllMocks(); });
afterEach(() => { cleanup(); vi.useRealTimers(); });
const open = async Page => {
  const view = render(<MemoryRouter><Page /></MemoryRouter>);
  await act(async () => {});
  return view;
};
it("keeps avatar cards mounted while searching instead of replacing them with skeletons", async () => {
  getAvatars.mockResolvedValueOnce({ data: { count: 1, results: [{ id: "a", name: "Saved avatar" }] } });
  getAvatars.mockReturnValueOnce(new Promise(() => {}));
  await open(Avatar);
  const card = screen.getByText("Saved avatar");
  fireEvent.change(screen.getByLabelText("Search avatars"), { target: { value: "another" } });
  await act(() => vi.advanceTimersByTimeAsync(500));
  expect(getAvatars).toHaveBeenCalledTimes(2);
  expect(screen.getByText("Saved avatar")).toBe(card);
  expect(screen.queryByRole("status")).toBeNull();
});
it("keeps video cards mounted while refreshing filtered results", async () => {
  getVideos.mockResolvedValueOnce({ data: { count: 1, results: [{ id: "v", title: "Saved project" }] } });
  getVideos.mockReturnValueOnce(new Promise(() => {}));
  await open(Videos);
  const card = screen.getByText("Saved project");
  fireEvent.change(screen.getByLabelText("Search videos"), { target: { value: "new search" } });
  await act(() => vi.advanceTimersByTimeAsync(500));
  expect(getVideos).toHaveBeenCalledTimes(2);
  expect(screen.getByText("Saved project")).toBe(card);
  expect(screen.getByRole("region", { name: "Video library" }).getAttribute("aria-busy")).toBe("true");
  expect(screen.queryByRole("status")).toBeNull();
});
it("keeps usage figures visible while changing the reporting period", async () => {
  getUsage.mockResolvedValueOnce({ ok: true, data: { totals: { characters: 400, images: 2, requests: 3 }, breakdown: [] } });
  getUsage.mockReturnValueOnce(new Promise(() => {}));
  await open(Usage);
  const figure = screen.getByText("400");
  fireEvent.change(screen.getByLabelText("Usage period"), { target: { value: "7" } });
  expect(getUsage).toHaveBeenCalledTimes(2);
  expect(screen.getByText("400")).toBe(figure);
  expect(screen.queryByText("Loading usage…")).toBeNull();
});
