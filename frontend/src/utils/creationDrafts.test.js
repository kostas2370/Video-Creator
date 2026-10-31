import { expect, it } from "vitest";
import { creationDraftKey, creationDraftOwner, restoreWizardDraft } from "./creationDrafts";

it("uses a stable account scope without persisting authentication tokens", () => {
  const token = `header.${btoa(JSON.stringify({ user_id: "account-1" }))}.signature`;
  expect(creationDraftOwner({}, token)).toBe("account-1");
  expect(creationDraftKey(creationDraftOwner({}, token), "series-new")).toBe("viddie:creation:v1:account-1:series-new");
  expect(creationDraftOwner({}, "invalid")).toBe("");
  expect(creationDraftKey("", "ai-video")).toBeNull();
});

it("restores valid values while discarding damaged form fields and step numbers", () => {
  const defaults = { form: { title: "", scene_count: 6, cast: [] }, step: 0, ui: {} };
  expect(restoreWizardDraft({ form: { title: {}, scene_count: "9", cast: [null, { id: "1", name: "Milo", appearance: "Fox" }] }, step: 99, ui: { proposal: {} } }, defaults)).toEqual({ form: { title: "", scene_count: "9", cast: [{ id: "1", name: "Milo", appearance: "Fox" }] }, step: 0, ui: { proposal: {} } });
});
