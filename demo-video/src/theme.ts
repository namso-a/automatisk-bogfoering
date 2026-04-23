/**
 * Kvitly design tokens — matches the form.html landing aesthetic.
 * Background: warm off-white, text: deep espresso, accent: brass/amber.
 */

export const COLORS = {
  paper: "#fafaf7",
  ink: "#1a1612",
  accent: "#9a6f28",
  accentHover: "#7d5a20",
  muted: "#8a817a",
  warm: "#e8e4d8",
  warmDark: "#d6d0c0",
  successBg: "#e6f2e6",
  successInk: "#2d5a2d",
  white: "#ffffff",
  black: "#000000",
} as const;

export const FONTS = {
  heading: "Fraunces, Georgia, serif",
  body: "Inter, system-ui, sans-serif",
} as const;

export const RADIUS = {
  sm: 4,
  md: 6,
} as const;

/** Frame rate for all compositions */
export const FPS = 30;

/** Total duration in frames: 60 seconds × 30fps = 1800 */
export const TOTAL_FRAMES = 1800;

/** Scene boundaries in frames */
export const SCENES = {
  title: { start: 0, end: 150 },        // 0–5s
  problem: { start: 150, end: 450 },    // 5–15s
  upload: { start: 450, end: 900 },     // 15–30s
  dashboard: { start: 900, end: 1500 }, // 30–50s
  outro: { start: 1500, end: 1800 },    // 50–60s
} as const;

/** Google Fonts import string — inject via @font-face in composition */
export const GOOGLE_FONTS_URL =
  "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;1,9..144,300;1,9..144,400;1,9..144,500&family=Inter:wght@400;500;600&display=swap";
