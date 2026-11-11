// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({
  getMediaAssets: vi.fn(), createMediaAsset: vi.fn(), editMediaAsset: vi.fn(),
  deleteMediaAsset: vi.fn(), downloadMediaAsset: vi.fn(), getMusicCatalog: vi.fn(), downloadMusicCatalogTrack: vi.fn(),
}));
vi.mock("./ui/ConfirmationDialog", () => ({ ConfirmationDialog: () => null }));
vi.mock("./ui/EditorDialog", () => ({ EditorDialog: () => null, editorInput: "", editorButton: "" }));
import { getMediaAssets, getMusicCatalog } from "../api/apiService";
import { MediaLibrary } from "./MediaLibrary";

beforeEach(() => {
  vi.clearAllMocks();
  getMediaAssets.mockResolvedValue({ ok: true, data: { count: 1, results: [
    { id: "private", title: "My track", kind: "AUDIO", file: "/private.wav", tags: [] },
  ] } });
  getMusicCatalog.mockResolvedValue({ ok: true, data: { count: 1, results: [
    { id: "shared", title: "General track", kind: "AUDIO", file: "/shared.wav", tags: ["fun"], is_shared: true,
      attribution: "Music by Artist", license_url: "https://example.com/license" },
  ] } });
});
afterEach(cleanup);

it("offers general music while restricting edit and remove controls to private tracks", async () => {
  const onSelect = vi.fn();
  render(<MediaLibrary kind="AUDIO" onSelect={onSelect} />);
  await screen.findByText("My track");
  expect(screen.getAllByRole("button", { name: "Edit tags" })).toHaveLength(1);
  expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("Media collection"), { target: { value: "shared" } });
  await screen.findByText("General track");
  expect(screen.queryByRole("button", { name: "Edit tags" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  expect(screen.getByText("Music by Artist")).toBeTruthy();
  expect(screen.getByRole("link", { name: "License" }).getAttribute("href")).toBe("https://example.com/license");
  fireEvent.click(screen.getByRole("button", { name: "Use media" }));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "shared" }));
});

it("uses separate APIs for private media and the general catalog", async () => {
  render(<MediaLibrary kind="AUDIO" />);
  await screen.findByText("My track");
  fireEvent.change(screen.getByLabelText("Media collection"), { target: { value: "shared" } });
  await waitFor(() => expect(getMusicCatalog).toHaveBeenLastCalledWith("", 1));
  fireEvent.change(screen.getByLabelText("Media collection"), { target: { value: "private" } });
  await waitFor(() => expect(getMediaAssets).toHaveBeenLastCalledWith("", 1, "AUDIO"));
});
