import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { EpisodeCard, SeriesHeader } from "../pages/SeriesPage";
import { EpisodeComposer, SeriesLibraryCard, SeriesOverview } from "./SeriesWorkspacePanels";
import { SeriesProfileForm } from "./SeriesProfileForm";

describe("series workspace", () => {
  it("explains continuity and captures a reusable setup", () => {
    const html = renderToStaticMarkup(<><SeriesHeader /><SeriesProfileForm busy={false} onSave={() => {}} /></>);
    expect(html).toContain("A familiar world. A new story.");
    expect(html).toContain("Recurring characters");
    expect(html).toContain("Signature visual style");
    expect(html).toContain("Voice-over");
    expect(html).toContain("References improve consistency; generated appearances can still vary.");
  });
  it("keeps memory editable even after the original video is deleted", () => {
    const html = renderToStaticMarkup(<MemoryRouter><EpisodeCard episode={{ id: "ep", number: 3, idea: "A new discovery", summary: "Milo found a lantern", video_id: null, is_canon: true }} /></MemoryRouter>);
    expect(html).toContain("Video removed");
    expect(html).toContain("Milo found a lantern");
    expect(html).toContain("Ready for future episodes");
    expect(html).not.toContain("Open episode");
  });
  it("offers draft retry when queuing failed and directs reviewed drafts to the editor", () => {
    const html = renderToStaticMarkup(<MemoryRouter><EpisodeCard episode={{ id: "ep", number: 1, idea: "First", summary: "", video_id: "vid", status: "FAILED", can_retry: true }} /></MemoryRouter>);
    expect(html).toContain("Retry draft");
    expect(html).toContain('/videos/vid/');
    const review = renderToStaticMarkup(<MemoryRouter><EpisodeCard episode={{ id: "ep", number: 1, idea: "First", summary: "Draft events", video_id: "vid", status: "REVIEW", can_retry: false }} /></MemoryRouter>);
    expect(review).toContain("Review storyboard");
    expect(review).not.toContain("Retry draft");
  });
});

it("marks changed stories for review and offers an explicit memory draft", () => {
  const html = renderToStaticMarkup(<MemoryRouter><EpisodeCard episode={{ id: "ep", number: 2, summary: "Previous events", video_id: "vid", status: "READY", is_canon: true, memory_needs_review: true, can_update_memory: true }} /></MemoryRouter>);
  expect(html).toContain("Needs review");
  expect(html).toContain("Update memory from current script");
  expect(html).toContain("Review the draft before saving");
});

it("replaces drafting with one clear continuation action for an active episode", () => {
  const html = renderToStaticMarkup(<MemoryRouter><EpisodeComposer profile={{ active_episode: { number: 8, video_id: "active-video" } }} /></MemoryRouter>);
  expect(html).toContain("Continue episode 8");
  expect(html).toContain("/videos/active-video/");
  expect(html).not.toContain("textarea");
  expect(html).not.toContain('type="submit"');
});

it("requires cast setup before offering episode drafting for story series", () => {
  const html = renderToStaticMarkup(<EpisodeComposer profile={{ cast_ready: false }} />);
  expect(html).toContain("Create and approve your characters first");
  expect(html).toContain("Set up your cast");
  expect(html).not.toContain("textarea");
});
it("explains first episode creation and disables drafting while setup is being edited", () => {
  const html = renderToStaticMarkup(<EpisodeComposer profile={{ episode_count: 0 }} idea="A discovery" editing onSubmit={() => {}} />);
  expect(html).toContain("Let’s make episode one");
  expect(html).toContain("Review storyboard");
  expect(html).toContain("Save or close series setup before drafting");
  expect(html).toMatch(/type="submit" disabled/);
});
it("shows saved production choices and directs library cards to active work", () => {
  const profile = { id: "series", title: "Milo", premise: "A fox learns", video_format: "PORTRAIT", scene_count: 6, narration: false, subtitles: true, active_episode: { number: 4 } };
  const overview = renderToStaticMarkup(<SeriesOverview profile={profile} />);
  expect(overview).toContain("Portrait 9:16");
  expect(overview).toContain("6 shots");
  expect(overview).toContain("No narration");
  const card = renderToStaticMarkup(<MemoryRouter><SeriesLibraryCard series={profile} /></MemoryRouter>);
  expect(card).toContain("Continue episode 4");
  expect(card).toContain("/series/series/");
});
