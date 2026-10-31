// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ draftSeriesCast: vi.fn(), createCharacterReference: vi.fn(), getCharacterReference: vi.fn() }));
import * as api from "../api/apiService";
import { CharacterImageControls } from "./CharacterImageControls";
import { SeriesCastDesigner } from "./SeriesCastDesigner";
import { characterApproval, characterIsApproved } from "../utils/series";

const character = { id: "char-1", name: "Milo", appearance: "Orange fox", wardrobe: "Teal scarf", reference_id: "old-ref", reference_image: "/media/old.png" };
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

it("reviews an AI cast before replacing existing character cards", async () => {
  const onUse = vi.fn();
  api.draftSeriesCast.mockResolvedValue({ ok: true, data: { cast: [character] } });
  render(<SeriesCastDesigner premise="Fox adventures" visualStyle="Watercolor" storyFormat="ANIMATED_STORY" hasCast onUse={onUse} />);
  fireEvent.click(screen.getByRole("button", { name: "Create characters with AI" }));
  await screen.findByText("Review proposed cast");
  expect(onUse).not.toHaveBeenCalled();
  expect(api.createCharacterReference).not.toHaveBeenCalled();
  expect(api.draftSeriesCast).toHaveBeenCalledWith({ premise: "Fox adventures", visual_style: "Watercolor", story_format: "ANIMATED_STORY", count: 2 });
  fireEvent.click(screen.getByRole("button", { name: "Use proposed cast" }));
  expect(onUse).toHaveBeenCalledWith([character]);
});

it("keeps the previous reference until a queued AI image is reviewed and accepted", async () => {
  api.createCharacterReference.mockResolvedValue({ ok: true, data: { id: "new-ref", status: "QUEUED" } });
  api.getCharacterReference.mockResolvedValue({ ok: true, data: { id: "new-ref", status: "READY", image: "/media/new.png" } });
  const onPatch = vi.fn();
  render(<CharacterImageControls character={character} visualStyle="Watercolor" onPatch={onPatch} />);
  fireEvent.click(screen.getByRole("button", { name: "Generate another look with AI" }));
  await screen.findByText("Review new character image");
  expect(onPatch).toHaveBeenCalledWith({ reference_job_id: "new-ref" });
  expect(screen.getByAltText("Milo approved reference").getAttribute("src")).toBe("/media/old.png");
  fireEvent.click(screen.getByRole("button", { name: "Use this look" }));
  expect(onPatch).toHaveBeenCalledWith({ reference_id: "new-ref", reference_job_id: null, reference_image: "/media/new.png", reference_approval: characterApproval({ ...character, reference_id: "new-ref" }, "Watercolor") });
});

it("preserves the previous look and shows the saved job failure", async () => {
  api.createCharacterReference.mockResolvedValue({ ok: true, data: { id: "job", status: "QUEUED" } });
  api.getCharacterReference.mockResolvedValue({ ok: true, data: { status: "FAILED", error: "Image provider unavailable" } });
  const onPatch = vi.fn();
  render(<CharacterImageControls character={character} visualStyle="Watercolor" onPatch={onPatch} />);
  fireEvent.click(screen.getByRole("button", { name: "Generate another look with AI" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Image provider unavailable");
  expect(onPatch.mock.calls.every(([patch]) => !patch.reference_id)).toBe(true);
  expect(screen.getByAltText("Milo approved reference")).toBeTruthy();
});

it("uploads an image for review without triggering paid generation", async () => {
  api.createCharacterReference.mockResolvedValue({ ok: true, data: { id: "upload-ref", status: "READY", image: "/media/upload.png" } });
  render(<CharacterImageControls character={character} visualStyle="Watercolor" onPatch={vi.fn()} />);
  const image = new File(["image"], "reference.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText("Upload reference for Milo"), { target: { files: [image] } });
  await screen.findByText("Review new character image");
  const payload = api.createCharacterReference.mock.calls[0][0];
  expect(payload).toBeInstanceOf(FormData);
  expect(payload.get("name")).toBe("Milo");
  expect(payload.get("image").name).toBe("reference.png");
  expect(api.getCharacterReference).not.toHaveBeenCalled();
});

it("requires reviewing visual changes while allowing story and personality edits", () => {
  const approved = { ...character, reference_approval: characterApproval(character, "Watercolor") };
  expect(characterIsApproved(approved, "Watercolor")).toBe(true);
  expect(characterIsApproved({ ...approved, personality: "Brave" }, "Watercolor")).toBe(true);
  expect(characterIsApproved({ ...approved, wardrobe: "Red coat" }, "Watercolor")).toBe(false);
  expect(characterIsApproved({ ...approved, reference_id: "other" }, "Watercolor")).toBe(false);
  expect(characterIsApproved(approved, "Photorealistic")).toBe(false);
});

it("resumes a saved image request without making another paid request", async () => {
  api.getCharacterReference.mockResolvedValue({ ok: true, data: { id: "saved-job", status: "READY", image: "/media/recovered.png" } });
  render(<CharacterImageControls character={{ ...character, reference_job_id: "saved-job" }} visualStyle="Watercolor" onPatch={vi.fn()} />);
  await screen.findByText("Review new character image");
  expect(api.getCharacterReference).toHaveBeenCalledWith("saved-job");
  expect(api.createCharacterReference).not.toHaveBeenCalled();
});
