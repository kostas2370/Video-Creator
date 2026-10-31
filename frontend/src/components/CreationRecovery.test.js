// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => ({}) }));
vi.mock("../api/apiService", async importOriginal => ({ ...await importOriginal(), getAvatars: vi.fn(), getTemplates: vi.fn(), getVoices: vi.fn(), getIntro: vi.fn(), getOutro: vi.fn(), getCustomVisualProviders: vi.fn(), generateVideo: vi.fn(), draftCharacterDescription: vi.fn(), draftSeriesCast: vi.fn(), createCharacterReference: vi.fn(), getCharacterReference: vi.fn() }));
vi.mock("../utils/draftFiles", () => ({ readDraftFile: vi.fn(), writeDraftFile: vi.fn() }));
import * as api from "../api/apiService";
import * as files from "../utils/draftFiles";
import AuthContext from "../store/AuthContext";
import { creationDraftKey } from "../utils/creationDrafts";
import { SeriesProfileForm } from "./SeriesProfileForm";
import Home from "../pages/HomePage";

let savedFiles;
const wrap = (element, owner = "alice") => <MemoryRouter><AuthContext.Provider value={{ user: { id: owner }, setAccessToken() {}, setCSRFToken() {} }}>{element}</AuthContext.Provider></MemoryRouter>;
const startSeries = () => {
  fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Fox mysteries" } });
  fireEvent.change(screen.getByLabelText("What is this series about?"), { target: { value: "A fox detective solves mysteries" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to cast" }));
};
beforeEach(() => {
  vi.clearAllMocks(); localStorage.clear(); savedFiles = new Map();
  [api.getAvatars, api.getTemplates, api.getVoices, api.getIntro, api.getOutro].forEach(fn => fn.mockResolvedValue({ ok: true, data: { results: [], next: null } }));
  api.getCustomVisualProviders.mockResolvedValue({ ok: true, data: [] });
  api.generateVideo.mockResolvedValue({ ok: false });
  files.readDraftFile.mockImplementation(async key => savedFiles.get(key) || null);
  files.writeDraftFile.mockImplementation(async (key, file) => { if (file) savedFiles.set(key, file); else savedFiles.delete(key); });
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:restored-reference");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); delete window.confirm; });

it("restores the series step, selected character and unaccepted AI description without requesting it again", async () => {
  const draft = { name: "Milo", appearance: "Orange fox", wardrobe: "Teal scarf", personality: "Curious detective", relationships: "" };
  api.draftCharacterDescription.mockResolvedValue({ ok: true, data: { character: draft } });
  const first = render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Add character" }));
  fireEvent.change(screen.getByLabelText("Character 1 name"), { target: { value: "Milo" } });
  fireEvent.change(screen.getByLabelText(/Character idea/), { target: { value: "A shy detective" } });
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  await screen.findByText("Description draft");
  first.unmount();
  render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  expect(screen.getByRole("heading", { name: "Meet your characters" })).toBeTruthy();
  expect(screen.getByLabelText("Series name").value).toBe("Fox mysteries");
  expect(screen.getByLabelText("Character 1 name").value).toBe("Milo");
  expect(screen.getByLabelText(/Character idea/).value).toBe("A shy detective");
  expect(screen.getByText("Description draft")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Use description" })).toBeTruthy();
  expect(api.draftCharacterDescription).toHaveBeenCalledOnce();
});

it("recovers a proposed cast before it is accepted", async () => {
  api.draftSeriesCast.mockResolvedValue({ ok: true, data: { cast: [{ id: "milo", name: "Milo", appearance: "Orange fox", wardrobe: "", personality: "Curious", relationships: "" }] } });
  const first = render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Create characters with AI" }));
  await screen.findByText("Review proposed cast");
  first.unmount();
  render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  expect(screen.getByText("Review proposed cast")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Use proposed cast" })).toBeTruthy();
  expect(api.draftSeriesCast).toHaveBeenCalledOnce();
});

it("resumes checking the saved character image job without starting a paid replacement", async () => {
  api.createCharacterReference.mockResolvedValue({ ok: true, data: { id: "image-job", status: "QUEUED" } });
  api.getCharacterReference.mockImplementation(() => new Promise(() => {}));
  const first = render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Add character" }));
  fireEvent.change(screen.getByLabelText("Character 1 name"), { target: { value: "Milo" } });
  fireEvent.change(screen.getByLabelText("Fixed appearance"), { target: { value: "Orange fox" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate character image with AI" }));
  await waitFor(() => expect(JSON.parse(localStorage.getItem(creationDraftKey("alice", "series-new"))).value.form.cast[0].reference_job_id).toBe("image-job"));
  first.unmount();
  api.getCharacterReference.mockResolvedValue({ ok: true, data: { id: "image-job", status: "READY", image: "/media/milo.png" } });
  render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  await screen.findByText("Review new character image");
  expect(api.createCharacterReference).toHaveBeenCalledOnce();
});

it("keeps drafts private to their account and editing scope", () => {
  const first = render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Alice private draft" } });
  first.unmount();
  const second = render(wrap(<SeriesProfileForm onSave={vi.fn()} />, "bob"));
  expect(screen.getByLabelText("Series name").value).toBe("");
  second.unmount();
  render(wrap(<SeriesProfileForm initial={{ id: "existing", title: "Saved series", premise: "Saved premise", visual_style: "Watercolor" }} onSave={vi.fn()} />));
  expect(screen.getByLabelText("Series name").value).toBe("Saved series");
});

it("clears a draft after successful save and ignores a late response after starting over", async () => {
  let finish;
  api.draftCharacterDescription.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  window.confirm = vi.fn().mockReturnValue(true);
  render(wrap(<SeriesProfileForm onSave={vi.fn().mockResolvedValue({ ok: true })} />));
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Add character" }));
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  fireEvent.click(screen.getByRole("button", { name: "Start over" }));
  await act(async () => finish({ ok: true, data: { character: { name: "Old", appearance: "Old look" } } }));
  expect(localStorage.getItem(creationDraftKey("alice", "series-new"))).toBeNull();
  expect(screen.getByLabelText("Series name").value).toBe("");
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Continue to finish" }));
  fireEvent.click(screen.getByRole("button", { name: "Create series" }));
  await waitFor(() => expect(localStorage.getItem(creationDraftKey("alice", "series-new"))).toBeNull());
});

it("restores uploaded reference files and includes the recovered file in the explicit generation request", async () => {
  const first = render(wrap(<Home />));
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "A watercolor fox story" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to look & sound" }));
  fireEvent.change(screen.getByLabelText("Visuals"), { target: { value: "AI" } });
  const file = new File(["reference bytes"], "cast-reference.png", { type: "image/png" });
  fireEvent.change(first.container.querySelector("#reference-image"), { target: { files: [file] } });
  await waitFor(() => expect(savedFiles.size).toBe(1));
  first.unmount();
  render(wrap(<Home />));
  await screen.findByAltText("Reference preview");
  expect(screen.getByLabelText("Visuals").value).toBe("AI");
  expect(api.generateVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Review video" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Draft storyboard" }).disabled).toBe(false));
  fireEvent.click(screen.getByRole("button", { name: "Draft storyboard" }));
  await waitFor(() => expect(api.generateVideo).toHaveBeenCalledOnce());
  const recovered = api.generateVideo.mock.calls[0][0].get("reference_image");
  expect(recovered.name).toBe(file.name);
  expect(recovered.size).toBe(file.size);
});

it("reopens an existing storyboard project instead of generating it again", async () => {
  localStorage.setItem(creationDraftKey("alice", "ai-video"), JSON.stringify({ version: 1, value: { form: { message: "My existing story" }, step: 2, pendingVideoId: "saved-project", ui: {} } }));
  render(wrap(<Home />));
  expect(screen.getAllByRole("link", { name: "Open saved project" }).every(link => link.getAttribute("href") === "/videos/saved-project/")).toBe(true);
  expect(screen.queryByRole("button", { name: "Draft storyboard" })).toBeNull();
  expect(api.generateVideo).not.toHaveBeenCalled();
});

it("keeps the draft when saving the series fails", async () => {
  const onSave = vi.fn().mockResolvedValue({ ok: false });
  render(wrap(<SeriesProfileForm onSave={onSave} />));
  startSeries();
  fireEvent.click(screen.getByRole("button", { name: "Continue to finish" }));
  fireEvent.click(screen.getByRole("button", { name: "Create series" }));
  await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
  expect(JSON.parse(localStorage.getItem(creationDraftKey("alice", "series-new"))).value.form.title).toBe("Fox mysteries");
});

it("requires reattaching or explicitly removing an unavailable saved reference before generation", async () => {
  localStorage.setItem(creationDraftKey("alice", "ai-video"), JSON.stringify({ version: 1, value: { form: { message: "Fox story", image_mode: "AI", provider: "OPENAI" }, step: 2, hasReferenceFile: true, ui: {} } }));
  render(wrap(<Home />));
  await screen.findByText(/browser could not recover it/);
  expect(screen.getByRole("button", { name: "Draft storyboard" }).disabled).toBe(true);
  expect(api.generateVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Remove this reference" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Draft storyboard" }).disabled).toBe(false));
});

it("reports browser storage errors instead of claiming the draft is saved", () => {
  const storage = localStorage;
  vi.stubGlobal("localStorage", { getItem: storage.getItem.bind(storage), removeItem: storage.removeItem.bind(storage), setItem: () => { throw new Error("Quota exceeded"); } });
  render(wrap(<SeriesProfileForm onSave={vi.fn()} />));
  fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Important draft" } });
  expect(screen.getByRole("status").textContent).toContain("could not save this draft");
});
