import { expect, it } from "vitest";
import { diagramPlan } from "./diagrams";
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
