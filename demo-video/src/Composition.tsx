import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { DashboardScene } from "./scenes/DashboardScene";
import { OutroScene } from "./scenes/OutroScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { TitleScene } from "./scenes/TitleScene";
import { UploadScene } from "./scenes/UploadScene";
import { SCENES, TOTAL_FRAMES } from "./theme";

/**
 * Main Kvitly demo composition.
 *
 * Duration: 60 seconds at 30fps = 1800 frames.
 *
 * Scene layout:
 * ┌──────────────────────────────────────────────────────────────────┐
 * │  TitleScene     0–150    (0–5s)   │ Kvitly logo + wordmark       │
 * │  ProblemScene   150–450  (5–15s)  │ Messenger chaos              │
 * │  UploadScene    450–900  (15–30s) │ Form capture + callouts      │
 * │  DashboardScene 900–1500 (30–50s) │ Dashboard capture + callouts │
 * │  OutroScene     1500–1800(50–60s) │ Logo + URL + CTA             │
 * └──────────────────────────────────────────────────────────────────┘
 *
 * Each scene is wrapped in a <Sequence> so Remotion resets useCurrentFrame()
 * to 0 at the start of each one, making scene-local timing simple.
 */
export const KvitlyComposition: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Title: frames 0–150 (5s) */}
      <Sequence
        from={SCENES.title.start}
        durationInFrames={SCENES.title.end - SCENES.title.start}
        name="Title"
      >
        <TitleScene />
      </Sequence>

      {/* Problem: frames 150–450 (10s) */}
      <Sequence
        from={SCENES.problem.start}
        durationInFrames={SCENES.problem.end - SCENES.problem.start}
        name="Problem"
      >
        <ProblemScene />
      </Sequence>

      {/* Upload: frames 450–900 (15s) */}
      <Sequence
        from={SCENES.upload.start}
        durationInFrames={SCENES.upload.end - SCENES.upload.start}
        name="Upload"
      >
        <UploadScene />
      </Sequence>

      {/* Dashboard: frames 900–1500 (20s) */}
      <Sequence
        from={SCENES.dashboard.start}
        durationInFrames={SCENES.dashboard.end - SCENES.dashboard.start}
        name="Dashboard"
      >
        <DashboardScene />
      </Sequence>

      {/* Outro: frames 1500–1800 (10s) */}
      <Sequence
        from={SCENES.outro.start}
        durationInFrames={SCENES.outro.end - SCENES.outro.start}
        name="Outro"
      >
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};

// Export total duration for use in Root.tsx
export { TOTAL_FRAMES };
