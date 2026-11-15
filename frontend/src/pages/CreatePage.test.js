// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", async importOriginal => ({ ...await importOriginal(), getVideos: vi.fn() }));
import { getVideos } from "../api/apiService";
import CreatePage from "./CreatePage";
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const open = () => render(<MemoryRouter><CreatePage /></MemoryRouter>);

it("features two starting points while keeping all specialist tools reachable", async () => {
  getVideos.mockResolvedValue({ ok: true, data: { results: [] } });
  open();
  const featured = within(screen.getByRole("region", { name: "Start a new video" }));
  expect(featured.getAllByRole("link").map(link => link.getAttribute("href"))).toEqual(["/ai/", "/manual/"]);
  const tools = within(screen.getByRole("region", { name: "More ways to create" }));
  expect(tools.getAllByRole("link").map(link => link.getAttribute("href"))).toEqual(["/clips/", "/series/", "/story/", "/captions/"]);
  expect(await screen.findByText("Start a video below. Your recent projects will appear here.")).toBeTruthy();
});

it("shows the three most recently edited projects with statuses and editor links", async () => {
  getVideos.mockResolvedValue({ ok: true, data: { results: [
    { id: 12, title: "Fox mystery", status: "REVIEW" },
    { id: 8, title: "Island trip", status: "COMPLETED" },
    { id: 6, title: "", status: "FAILED" },
    { id: 1, title: "Older video", status: "READY" },
  ] } });
  open();
  await screen.findByText("Fox mystery");
  expect(getVideos).toHaveBeenCalledWith("", 1, "", { ordering: "-updated_at" });
  expect(screen.getByText("Review script")).toBeTruthy();
  expect(screen.getByText("Export ready")).toBeTruthy();
  expect(screen.getByText("Needs attention")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Continue editing Fox mystery" }).getAttribute("href")).toBe("/videos/12/");
  expect(screen.getByRole("link", { name: "Continue editing Untitled video" }).getAttribute("href")).toBe("/videos/6/");
  expect(screen.queryByText("Older video")).toBeNull();
});

it("keeps creation available during a library failure and lets users retry", async () => {
  getVideos.mockResolvedValueOnce({ ok: false, data: null }).mockResolvedValueOnce({ ok: true, data: { results: [] } });
  open();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Create with AI" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("Start a video below. Your recent projects will appear here.");
  expect(getVideos).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("alert")).toBeNull();
});
