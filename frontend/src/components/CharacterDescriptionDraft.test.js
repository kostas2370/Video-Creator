// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { draftCharacterDescription } from "../api/apiService";
import { CharacterDescriptionDraft } from "./CharacterDescriptionDraft";
import { SeriesCastEditor } from "./SeriesCastEditor";

vi.mock("../api/apiService", () => ({ draftCharacterDescription: vi.fn() }));
vi.mock("./CharacterImageControls", () => ({ CharacterImageControls: () => null }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const draft = { name: "Rin", appearance: "Grey fox", wardrobe: "Blue coat", personality: "Clever rival", relationships: "Milo’s rival" };
const props = { character: { id: "milo", name: "Milo", appearance: "Orange fox" }, premise: "Fox mysteries", visualStyle: "Watercolor", storyFormat: "GENERAL", castNames: ["Milo"] };

it("recovers from request errors and incomplete drafts without getting stuck", async () => {
  draftCharacterDescription.mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValueOnce({ ok: true, data: { character: { name: "Rin" } } })
    .mockResolvedValueOnce({ ok: true, data: { character: draft } });
  const use = vi.fn();
  render(<CharacterDescriptionDraft {...props} onUse={use} />);
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Offline");
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("incomplete"));
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  await screen.findByText("Description draft");
  expect(use).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Use description" }));
  expect(use).toHaveBeenCalledWith(draft);
});

it("adds a reviewed AI character with a fresh identity and preserves the existing cast", async () => {
  draftCharacterDescription.mockResolvedValue({ ok: true, data: { character: draft } });
  const original = { id: "milo", name: "Milo", appearance: "Orange fox", image: "/milo.png", image_approved: true };
  function Editor() {
    const [cast, change] = useState([original]);
    return <><SeriesCastEditor cast={cast} onChange={change} premise="Fox mysteries" visualStyle="Watercolor" /><output aria-label="Saved cast">{JSON.stringify(cast)}</output></>;
  }
  render(<Editor />);
  fireEvent.click(screen.getByRole("button", { name: "Add character with AI" }));
  fireEvent.change(screen.getByLabelText(/New character idea/), { target: { value: "A clever rival" } });
  fireEvent.click(screen.getByRole("button", { name: "Create character with AI" }));
  await screen.findByText("Review new character");
  expect(JSON.parse(screen.getByLabelText("Saved cast").textContent)).toEqual([original]);
  expect(draftCharacterDescription).toHaveBeenCalledWith(expect.objectContaining({ idea: "A clever rival", name: "", cast_names: ["Milo"] }));
  fireEvent.click(screen.getByRole("button", { name: "Add this character" }));
  const cast = JSON.parse(screen.getByLabelText("Saved cast").textContent);
  expect(cast[0]).toEqual(original);
  expect(cast[1]).toMatchObject(draft);
  expect(cast[1].id).not.toBe(original.id);
  expect(screen.getByRole("button", { name: "Edit character Rin" }).getAttribute("aria-pressed")).toBe("true");
});

it("explains missing setup and limits AI creation to six characters", () => {
  render(<CharacterDescriptionDraft {...props} premise="" onUse={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Write description with AI" }).disabled).toBe(true);
  expect(screen.getByText(/Add a series idea and visual style/)).toBeTruthy();
  cleanup();
  render(<SeriesCastEditor cast={Array.from({ length: 6 }, (_, i) => ({ id: String(i), name: `Character ${i}`, appearance: "Fox" }))} onChange={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Add character with AI" }).disabled).toBe(true);
});
