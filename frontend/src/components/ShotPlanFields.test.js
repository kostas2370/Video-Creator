import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ShotPlanFields } from "./ShotPlanFields";

const render = props => renderToStaticMarkup(React.createElement(ShotPlanFields, { onChange: () => {}, ...props }));

describe("storyboard shot planning", () => {
  it("displays the reviewed plan without losing framing, movement, action, or timing", () => {
    const markup = render({ plan: { shot_size: "CLOSE_UP", camera_movement: "PUSH_IN", subject_action: "Milo opens the box", target_duration: 4.5 } });
    expect(markup).toContain('value="CLOSE_UP" selected');
    expect(markup).toContain('value="PUSH_IN" selected');
    expect(markup).toContain("Milo opens the box");
    expect(markup).toContain('value="4.5"');
  });
  it("keeps legacy shots unspecified until the user adds directions", () => {
    const markup = render({});
    expect(markup.match(/value="" selected/g)).toHaveLength(2);
    expect(markup).toContain('value=""');
  });
  it("explains the duration behavior and prevents edits while generation starts", () => {
    expect(render({ narration: true })).toContain("Recorded narration sets the scene length");
    const markup = render({ narration: false, disabled: true });
    expect(markup).toContain("Sets the scene length without narration");
    expect(markup).toContain('<fieldset disabled=""');
  });
});
