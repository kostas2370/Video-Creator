import { describe, expect, it } from "vitest";
import { copyTagText, parseTagDraft, tagDraft } from "./videoTags";

describe("video tag editing and copying", () => {
  it("parses pasted hashtags and preserves keyword phrases and Unicode", () => {
    expect(parseTagDraft({ tiktok: "#OceanLife #Nature, #Φύση", youtube: "ocean life,  marine   animals\nWhale facts", search: "sea life, wildlife" })).toEqual({
      tiktok: ["OceanLife", "Nature", "Φύση"], youtube: ["ocean life", "marine animals", "Whale facts"], search: ["sea life", "wildlife"],
    });
  });
  it("deduplicates and allows clearing every tag group", () => {
    expect(parseTagDraft({ tiktok: "#Nature #nature", youtube: "Ocean, ocean", search: " , " })).toEqual({ tiktok: ["Nature"], youtube: ["Ocean"], search: [] });
    expect(parseTagDraft(tagDraft())).toEqual({ tiktok: [], youtube: [], search: [] });
  });
  it("round trips saved metadata and copies in the appropriate format", () => {
    const tags = { tiktok: ["OceanLife", "Nature"], youtube: ["ocean life", "marine animals"], search: ["ocean"] };
    expect(parseTagDraft(tagDraft(tags))).toEqual(tags);
    expect(copyTagText("tiktok", tags.tiktok)).toBe("#OceanLife #Nature");
    expect(copyTagText("youtube", tags.youtube)).toBe("ocean life, marine animals");
    expect(copyTagText("search", tags.search)).toBe("ocean");
  });
});
