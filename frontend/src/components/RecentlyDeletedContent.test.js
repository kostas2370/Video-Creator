import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { RecentlyDeletedContent } from "./RecentlyDeletedContent";

const scene = { id: "old", position: 2, text: "Recover this scene", expires_at: "2026-10-29T12:00:00Z" };
const result = { results: [scene], previous: null, next: 2 };
const render = props => renderToStaticMarkup(<RecentlyDeletedContent page={1} result={result} {...props} />);

describe("scene recovery states", () => {
  it("hides stale restore actions while refreshing or reporting an error", () => {
    const loading = render({ loading: true });
    expect(loading).toContain('role="status"');
    expect(loading).not.toContain("Restore scene");
    const failed = render({ error: "Connection lost" });
    expect(failed).toContain('role="alert"');
    expect(failed).toContain("Refresh list");
    expect(failed).not.toContain("Restore scene");
  });
  it("shows the empty state without pagination", () => {
    const html = render({ result: { results: [] } });
    expect(html).toContain("No scenes to recover.");
    expect(html).not.toContain('aria-label="Removed scene pages"');
  });
  it("shows the recovery deadline and disables restoration during processing", () => {
    const html = render({ disabled: true });
    expect(html).toContain("Recover this scene");
    expect(html).toContain(`dateTime="${scene.expires_at}"`);
    expect(html).toMatch(/disabled=""[^>]*>Restore scene/);
  });
  it("prevents further restores and pagination while a restore is in progress", () => {
    const html = render({ restoring: scene.id });
    expect(html).toContain("Restoring…");
    expect(html.match(/disabled=""/g)).toHaveLength(3);
  });
});
