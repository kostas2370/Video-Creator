import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ReorderableScenes, reorderScene } from "./ReorderableScenes";

vi.mock("./Scene", () => ({ Scene: ({ scene, index, nextScene, reorderHandle, transitionControl }) => <article id={`scene-${scene.id}`} data-number={index + 1} data-next={nextScene?.id}>{scene.text}{reorderHandle}{transitionControl}</article> }));

const scenes = [{ id: "first", text: "First scene" }, { id: "second", text: "Second scene" }, { id: "third", text: "Third scene" }];
const render = props => renderToStaticMarkup(<ReorderableScenes scenes={scenes} {...props} />);

describe("scene editing views", () => {
  it("focuses one scene with its original number, audio neighbor, and outgoing transition", () => {
    const html = render({ selectedSceneId: "second" });
    expect(html).toContain('id="scene-second" data-number="2" data-next="third"');
    expect(html).not.toContain('id="scene-first"');
    expect(html).not.toContain('id="scene-third"');
    expect(html).toContain("Transition to scene 3");
  });
  it("shows every scene in a horizontal storyboard with only the selected editor below", () => {
    const html = render({ selectedSceneId: "second" });
    expect(html).toContain('aria-label="Horizontal storyboard"');
    scenes.forEach((scene, i) => {
      expect(html).toContain(`aria-label="Edit scene ${i + 1}"`);
      expect(html).toContain(`aria-label="Move scene ${i + 1}"`);
    });
    expect(html.match(/<article/g)).toHaveLength(1);
    expect(html).toContain('id="scene-second" data-number="2" data-next="third"');
    expect(html).toContain("Transition to scene 3");
    expect(html).not.toContain("Transition to scene 2");
    expect(html).toContain("left and right arrow keys");
  });
  it("keeps the first scene editable when no selection is supplied", () => {
    expect(render({})).toContain('id="scene-first"');
  });
  it("moves scenes in either direction without mutating the source order", () => {
    expect(reorderScene(scenes, 0, 2).map(scene => scene.id)).toEqual(["second", "third", "first"]);
    expect(reorderScene(scenes, 2, 0).map(scene => scene.id)).toEqual(["third", "first", "second"]);
    expect(scenes.map(scene => scene.id)).toEqual(["first", "second", "third"]);
  });
  it("does not add an outgoing transition on the last scene", () => {
    expect(render({ selectedSceneId: "third" })).not.toContain("Transition style");
  });
});
