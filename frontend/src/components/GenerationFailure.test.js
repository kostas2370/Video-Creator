import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import { GenerationFailure } from "./GenerationFailure";

const markup = video => renderToStaticMarkup(<MemoryRouter><GenerationFailure video={video} /></MemoryRouter>);

it("shows a saved provider failure with a link to key settings", () => {
  const html = markup({ status: "FAILED", generation_error: { provider: "OpenAI", code: "credentials", message: "OpenAI rejected the API key." } });
  expect(html).toContain('role="alert"');
  expect(html).toContain("OpenAI rejected the API key.");
  expect(html).toContain('href="/api-keys/"');
});

it("hides old failures while generation runs or after success", () => {
  for (const status of ["GENERATION", "READY", "COMPLETED"]) expect(markup({ status, generation_error: { message: "Old failure" } })).toBe("");
});

it("shows generic failures without a provider settings link", () => {
  const html = markup({ status: "FAILED", generation_error: { message: "Please try again." } });
  expect(html).toContain("Please try again.");
  expect(html).not.toContain("API key settings");
  expect(markup({ status: "FAILED" })).toBe("");
});
