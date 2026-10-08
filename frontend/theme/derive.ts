// A website's theme overrides: the CSS variables that replace the theme's
// (theme.css) for its colours and fonts.
//
// The website renders them in Python (core.branding.theme_variables); the control
// plane's preview computes them here, as the form changes. Both must agree:
// test-cases.json holds the expected output, checked by both test suites.

import catalog from "./fonts.json" with { type: "json" };

export interface ThemeChoices {
  primary_color?: string;
  secondary_color?: string;
  background_color?: string;
  text_color?: string;
  font_body?: string;
  font_display?: string;
}

export type FontId = keyof typeof catalog.fonts;
export type FontRole = "body" | "display";

// The theme's light and dark text colours (base-100 and base-content).
export const LIGHT_CONTENT = "#fdfbf8";
export const DARK_CONTENT = "#1b100a";
// Light text on coloured buttons, like the default theme (3.6:1 on its orange),
// unless it falls under the WCAG ratio for bold text: dark text then.
export const MIN_LIGHT_CONTRAST = 3;
// Body text on the background: WCAG AA for normal text.
export const MIN_TEXT_CONTRAST = 4.5;
// Cards and borders: the background, shaded toward the text colour.
// In oklab: mixing in oklch loses the hue of near-greys (Chrome), turning them pink.
export const BASE_200_SHADE = "4%";
export const BASE_300_SHADE = "9%";

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
const FALLBACKS = {
  sans: "ui-sans-serif, system-ui, sans-serif",
  serif: "ui-serif, Georgia, serif",
};

export const fonts = catalog.fonts;
export const defaultFonts = catalog.defaults as Record<FontRole, FontId>;

export function isColor(value: string | undefined): value is string {
  return !!value && HEX_COLOR.test(value);
}

/** WCAG relative luminance of a #rrggbb colour. */
export function luminance(color: string): number {
  const channel = (value: number) => {
    const c = value / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const at = (i: number) => channel(parseInt(color.slice(i, i + 2), 16));
  return 0.2126 * at(1) + 0.7152 * at(3) + 0.0722 * at(5);
}

export function contrast(first: string, second: string): number {
  const [a, b] = [luminance(first), luminance(second)];
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

/** The text colour on ``background``: the theme's light one if it reads well enough. */
export function contentColor(background: string): string {
  return contrast(background, LIGHT_CONTENT) >= MIN_LIGHT_CONTRAST ? LIGHT_CONTENT : DARK_CONTENT;
}

/** The font for ``role``, if ``id`` is one of the catalog's for that role. */
export function font(id: string | undefined, role: FontRole) {
  const entry = id ? (fonts as Record<string, (typeof fonts)[FontId]>)[id] : undefined;
  return entry && (entry.roles as string[]).includes(role) ? entry : undefined;
}

export function fontStack(id: string, role: FontRole): string {
  const entry = font(id, role);
  if (!entry) return "";
  return `"${entry.family}", ${FALLBACKS[entry.kind as keyof typeof FALLBACKS]}`;
}

/** The fonts the website uses (to link their stylesheets), defaults included. */
export function fontsUsed(choices: ThemeChoices): FontId[] {
  const body = font(choices.font_body, "body") ? choices.font_body : defaultFonts.body;
  const display = font(choices.font_display, "display") ? choices.font_display : defaultFonts.display;
  return [...new Set([body, display])] as FontId[];
}

/** The CSS variables replacing the theme's; empty when the defaults are kept. */
export function themeVariables(choices: ThemeChoices): Record<string, string> {
  const variables: Record<string, string> = {};
  for (const name of ["primary", "secondary"] as const) {
    const color = choices[`${name}_color`];
    if (isColor(color)) {
      variables[`--color-${name}`] = color;
      variables[`--color-${name}-content`] = contentColor(color);
    }
  }
  if (isColor(choices.background_color)) {
    variables["--color-base-100"] = choices.background_color;
    const shade = (amount: string) =>
      `color-mix(in oklab, var(--color-base-100), var(--color-base-content) ${amount})`;
    variables["--color-base-200"] = shade(BASE_200_SHADE);
    variables["--color-base-300"] = shade(BASE_300_SHADE);
  }
  if (isColor(choices.text_color)) {
    variables["--color-base-content"] = choices.text_color;
  }
  if (font(choices.font_body, "body") && choices.font_body !== defaultFonts.body) {
    variables["--font-sans"] = fontStack(choices.font_body!, "body");
  }
  if (font(choices.font_display, "display") && choices.font_display !== defaultFonts.display) {
    variables["--font-display"] = fontStack(choices.font_display!, "display");
  }
  return variables;
}

/** The rule applying ``variables``, after the theme's stylesheet. */
export function themeRule(variables: Record<string, string>): string {
  const body = Object.entries(variables)
    .map(([name, value]) => `${name}:${value};`)
    .join("");
  return body ? `:root,[data-theme="light"]{${body}}` : "";
}
