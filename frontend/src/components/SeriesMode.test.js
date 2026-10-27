import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { EpisodeCard, SeriesHeader } from "../pages/SeriesPage";
import { SeriesProfileForm } from "./SeriesProfileForm";

describe("series workspace", () => {
  it("explains continuity and captures a reusable setup", () => {
    const html = renderToStaticMarkup(<><SeriesHeader /><SeriesProfileForm busy={false} onSave={() => {}} /></>);
    expect(html).toContain("A familiar world. A new story.");
    expect(html).toContain("Recurring characters");
    expect(html).toContain("Signature visual style");
    expect(html).toContain("Narrator");
    expect(html).toContain("References improve consistency; generated appearances can still vary.");
  });
  it("keeps memory editable even after the original video is deleted", () => {
    const html = renderToStaticMarkup(<MemoryRouter><EpisodeCard episode={{ id: "ep", number: 3, idea: "A new discovery", summary: "Milo found a lantern", video_id: null, is_canon: true }} /></MemoryRouter>);
    expect(html).toContain("Video removed");
    expect(html).toContain("Milo found a lantern");
    expect(html).toContain("Used by future episodes");
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
