// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ useMediaAsset: vi.fn(), useMusicCatalogTrack: vi.fn() }));
vi.mock("./ui/EditorDialog", () => ({ EditorDialog: ({ open, children }) => open ? <div>{children}</div> : null }));
vi.mock("./MediaLibrary", () => ({ MediaLibrary: ({ onSelect }) => <>
  <button onClick={() => onSelect({ id: "private" })}>Private</button>
  <button onClick={() => onSelect({ id: "catalog", is_shared: true })}>Catalog</button>
</> }));
import { useMediaAsset, useMusicCatalogTrack } from "../api/apiService";
import { LibraryPicker } from "./LibraryPicker";

beforeEach(() => { vi.clearAllMocks(); useMediaAsset.mockResolvedValue({ ok: true }); useMusicCatalogTrack.mockResolvedValue({ ok: true }); });
afterEach(cleanup);

it("uses the catalog endpoint for general music", async () => {
  const onSaved = vi.fn();
  render(<LibraryPicker open videoId="video" purpose="music" onSaved={onSaved} onClose={vi.fn()} />);
  fireEvent.click(screen.getByText("Catalog"));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(useMusicCatalogTrack).toHaveBeenCalledWith("catalog", expect.objectContaining({ video_id: "video", purpose: "music" }));
  expect(useMediaAsset).not.toHaveBeenCalled();
});

it("keeps private media on the existing library endpoint", async () => {
  render(<LibraryPicker open videoId="video" purpose="music" onSaved={vi.fn()} onClose={vi.fn()} />);
  fireEvent.click(screen.getByText("Private"));
  await waitFor(() => expect(useMediaAsset).toHaveBeenCalledOnce());
  expect(useMusicCatalogTrack).not.toHaveBeenCalled();
});
