import { describe, expect, it } from "vitest";
import { editorHistoryReducer, UNDO_HISTORY_LIMIT } from "./editorHistory";
import { sameSceneOrder } from "./editorWorkspace";

const empty = { videoId: "a", entries: [] };
const record = (state, entry, videoId = "a") => editorHistoryReducer(state, { type: "record", videoId, entry });

describe("editor undo history", () => {
  it("undoes removals and moves in reverse order", () => {
    const move = { type: "order", before: ["a", "b"], after: ["b", "a"] };
    const removal = { type: "remove", before: ["b", "a"], after: ["a"], sceneId: "b" };
    let state = record(record(empty, move), removal);
    expect(sameSceneOrder([{ id: "a" }], state.entries.at(-1).after)).toBe(true);
    state = editorHistoryReducer(state, { type: "consume", videoId: "a", entry: removal });
    expect(state.entries.at(-1)).toBe(move);
    expect(sameSceneOrder([{ id: "b" }, { id: "a" }], move.after)).toBe(true);
    expect(editorHistoryReducer(state, { type: "consume", videoId: "a", entry: move }).entries).toEqual([]);
  });
  it("does not consume newer history when an older request finishes", () => {
    const first = { type: "order" }, second = { type: "remove" };
    const state = record(record(empty, first), second);
    expect(editorHistoryReducer(state, { type: "consume", videoId: "a", entry: first })).toBe(state);
  });
  it("keeps project histories separate and can clear history after recovery", () => {
    const first = record(empty, { type: "remove" });
    const other = record(first, { type: "order" }, "b");
    expect(other.videoId).toBe("b");
    expect(other.entries).toHaveLength(1);
    expect(editorHistoryReducer(other, { type: "clear", videoId: "b" }).entries).toEqual([]);
  });
  it("bounds history and rejects undo after adding a new scene", () => {
    let state = empty;
    for (let index = 0; index < UNDO_HISTORY_LIMIT + 5; index += 1) {
      state = record(state, { before: ["a", "b"], after: ["a"], index });
    }
    expect(state.entries).toHaveLength(UNDO_HISTORY_LIMIT);
    expect(state.entries[0].index).toBe(5);
    expect(sameSceneOrder([{ id: "a" }, { id: "new" }], state.entries.at(-1).after)).toBe(false);
  });
});
