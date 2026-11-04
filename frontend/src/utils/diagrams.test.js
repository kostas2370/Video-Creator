import { expect, it } from "vitest";
import { diagramElementState, diagramPlan } from "./diagrams";
import fixtures from "../../../backend/apps/videomanagement/tests/composer/diagram_fixtures.json";

it("matches export layout and timing for every template and aspect ratio", () => {
  for (const row of fixtures) {
    const plan = diagramPlan(row.diagram, row.size, row.duration);
    expect(plan.length).toBe(row.plan.length);
    plan.forEach((element, index) => {
      for (const [key, value] of Object.entries(row.plan[index])) {
        if (typeof value === "number") expect(element[key]).toBeCloseTo(value, 8);
        else expect(element[key]).toEqual(value);
      }
    });
  }
});

it("moves flow markers in the arrow direction and repeats deterministically when seeking", () => {
  const diagram = { template: "flow", items: [{ label: "Source" }, { label: "Destination" }] };
  const plan = diagramPlan(diagram, [1080, 1920], 6);
  const marker = plan.find(element => element.motion);
  const period = marker.motion.period;
  const early = diagramElementState(marker, period * .25);
  const late = diagramElementState(marker, period * .75);
  expect(late.y).toBeGreaterThan(early.y);
  expect(late.y).toBeLessThan(marker.motion.to_y);
  expect(diagramElementState(marker, period * 1.25).y).toBeCloseTo(early.y, 8);
  expect(diagramElementState(marker, 0).y).toBe(marker.y);
  expect(plan.filter(element => element.kind === "text").every(element => element.start === 0)).toBe(true);
});

it("moves graph markers along routed horizontal and vertical legs when seeking", () => {
  const marker = { x: 0, y: 0, start: 0, reveal: .3, motion: { path: [[0, 0], [100, 0], [100, 100]], period: 2 } };
  expect(diagramElementState(marker, .5)).toMatchObject({ x: 50, y: 0 });
  expect(diagramElementState(marker, 1.5)).toMatchObject({ x: 100, y: 50 });
  expect(diagramElementState(marker, 2.5)).toMatchObject({ x: 50, y: 0 });
});
