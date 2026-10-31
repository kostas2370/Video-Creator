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

it("upgrades saved character images and approvals without keeping the old API fields", () => {
  const character = { id: "milo", name: "Milo", appearance: "Fox", wardrobe: "Scarf", reference_id: "milo", reference_image: "/media/milo.png" };
  character.reference_approval = { reference_id: "milo", name: "Milo", appearance: "Fox", wardrobe: "Scarf", visual_style: "3D" };
  const defaults = { form: { cast: [], visual_style: "3D" }, step: 0, ui: {} };
  const restored = restoreWizardDraft({ form: { cast: [character], visual_style: "3D" } }, defaults).form.cast[0];
  expect(restored).toEqual({ id: "milo", name: "Milo", appearance: "Fox", wardrobe: "Scarf", image: "/media/milo.png", image_approved: true, visual_style: "3D", status: "READY" });
  const changed = restoreWizardDraft({ form: { cast: [{ ...character, appearance: "Blue fox" }], visual_style: "3D" } }, defaults).form.cast[0];
  expect(changed.image_approved).toBe(false);
});

it("upgrades a saved pending image request so recovery polls its character ID", () => {
  const defaults = { form: { cast: [], visual_style: "3D" }, step: 0, ui: {} };
  const restored = restoreWizardDraft({ form: { cast: [{ id: "draft", name: "Milo", appearance: "Fox", reference_job_id: "existing-image-request" }] } }, defaults).form.cast[0];
  expect(restored.id).toBe("existing-image-request");
  expect(restored.status).toBe("QUEUED");
  expect(restored).not.toHaveProperty("reference_job_id");
});
