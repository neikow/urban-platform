import { describe, expect, it } from "vitest";

import { contrast, fontsUsed, themeRule, themeVariables } from "./derive";
import expected from "./test-cases.json" with { type: "json" };

describe("themeVariables (same cases as core.branding.theme_variables)", () => {
  for (const { name, choices, variables, fonts } of expected.cases) {
    it(name, () => {
      expect(themeVariables(choices)).toEqual(variables);
      expect(fontsUsed(choices)).toEqual(fonts);
    });
  }
});

describe("themeRule", () => {
  it("is empty with the defaults", () => {
    expect(themeRule({})).toBe("");
  });

  it("applies the variables to the theme's selectors", () => {
    expect(themeRule({ "--color-primary": "#003d82" })).toBe(
      ':root,[data-theme="light"]{--color-primary:#003d82;}',
    );
  });
});

describe("contrast", () => {
  it("is 21 for black on white", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21);
  });
});
