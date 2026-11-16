// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { NarrationLanguage } from "./NarrationLanguage";
import { restoreWizardDraft } from "../utils/creationDrafts";
import { defaultSeries, seriesPayload } from "../utils/series";
afterEach(cleanup);
it("accepts regional languages and can restore automatic language selection", () => {
  function Form() { const [value, setValue] = useState(""); return <NarrationLanguage value={value} onChange={setValue} />; }
  render(<Form />);
  const input = screen.getByRole("combobox", { name: "Narration language" });
  expect(input.placeholder).toContain("Automatic");
  fireEvent.change(input, { target: { value: "Portuguese (Brazil)" } });
  expect(input.value).toBe("Portuguese (Brazil)");
  fireEvent.change(input, { target: { value: "" } });
  expect(input.value).toBe("");
});
it("keeps the language through video and series browser drafts and series submission", () => {
  const saved = { form: { narration_language: "Greek" }, step: 1 };
  const video = restoreWizardDraft(saved, { form: { narration_language: "" }, step: 0 });
  expect(video.form.narration_language).toBe("Greek");
  const series = restoreWizardDraft(saved, { form: defaultSeries, step: 0 });
  expect(seriesPayload(series.form).narration_language).toBe("Greek");
  expect(seriesPayload(series.form, new Blob(["image"])).get("narration_language")).toBe("Greek");
  expect(restoreWizardDraft({ form: {}, step: 0 }, { form: defaultSeries, step: 0 }).form.narration_language).toBe("");
});
