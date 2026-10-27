import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ExportFailure } from "./ExportFailure";

describe("failed export recovery", () => {
  const video = { status: "FAILED", render_error: { message: "Your scenes are saved.", reference: "abc123" } };
  it("shows the saved failure reference and a retry action after reload", () => {
    const html = renderToStaticMarkup(<ExportFailure video={video} onRetry={() => {}} />);
    expect(html).toContain("Your scenes are saved.");
    expect(html).toContain("Reference: abc123");
    expect(html).toContain("Retry export");
  });
  it("does not offer export recovery for failed generation or a new running export", () => {
    expect(renderToStaticMarkup(<ExportFailure video={{ status: "FAILED" }} />)).toBe("");
    expect(renderToStaticMarkup(<ExportFailure video={{ ...video, status: "RENDERING" }} />)).toBe("");
  });
  it("disables retry while an edit is pending", () => {
    expect(renderToStaticMarkup(<ExportFailure video={video} disabled />)).toContain('disabled=""');
  });
});
