# Kvitly Demo Video — Scripts

This directory contains the Playwright screen capture script used to generate
the raw recordings that Remotion composites into the final demo video.

---

## Prerequisites

- **Node.js 18+** — `node --version`
- **Flask app running** — `python app.py` from the project root (port 5000)
- **Playwright Chromium** — run once: `npx playwright install chromium`

---

## Full pipeline (capture + render)

```bash
cd demo-video
npm install
npx playwright install chromium    # first time only
npm run build                       # runs capture then render
```

The final MP4 is written to `out/kvitly-demo.mp4`.

---

## Step-by-step

### 1. Install dependencies

```bash
npm install
```

### 2. Install Playwright browser (first time only)

```bash
npx playwright install chromium
```

### 3. Start the Flask app

In a separate terminal, from the project root:

```bash
python app.py
```

### 4. Capture screen recordings

```bash
npm run capture
```

This runs `scripts/capture-screens.ts` via `ts-node`. It:

1. Launches headless Chromium at 1920×1080
2. Records the form page (`/`) — types a name, selects payment type, chooses udvalg
3. Saves `public/form-capture.webm`
4. Records the dashboard — logs in, scrolls through the expense table
5. Saves `public/dashboard-capture.webm`

### 5. Preview in Remotion Studio

```bash
npm run preview
```

Opens the Remotion Studio at `http://localhost:3000`. You can scrub through
all scenes, adjust timing, and tweak text without re-running capture.

### 6. Render final MP4

```bash
npm run render
```

Renders `out/kvitly-demo.mp4` (1920×1080, H.264, 60 seconds).

---

## Customising scene timing and text

All timing constants live in `src/theme.ts`:

```ts
export const SCENES = {
  title:     { start: 0,    end: 150  },   // 0–5s
  problem:   { start: 150,  end: 450  },   // 5–15s
  upload:    { start: 450,  end: 900  },   // 15–30s
  dashboard: { start: 900,  end: 1500 },   // 30–50s
  outro:     { start: 1500, end: 1800 },   // 50–60s
};
```

Callout text and individual fade-in frames are in each scene file under
`src/scenes/`. For example, to change the dashboard callout text:

```ts
// src/scenes/DashboardScene.tsx
<CalloutBubble
  text="Forbrug per udvalg"   // change this
  startFrame={150}
  right={40}
  top={200}
/>
```

---

## Exporting a 30-second short version

The `Root.tsx` registers a second composition called `KvitlyShort`
(frames 0–900, covering Title + Problem + Upload). Render it with:

```bash
npx remotion render src/Root.tsx KvitlyShort out/kvitly-short.mp4 --codec=h264
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Flask app not reachable` | Start Flask: `python app.py` |
| `No .webm file found` | Check Playwright installed: `npx playwright install chromium` |
| `Video file not found` in Remotion | Run `npm run capture` first |
| Remotion Studio blank screen | Check `src/Root.tsx` imports and `public/` file paths |
| Dashboard login fails | Verify `DASHBOARD_PASSWORD` in `.env` matches the script's password |
