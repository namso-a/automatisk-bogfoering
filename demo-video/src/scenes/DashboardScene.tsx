import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONTS } from "../theme";

interface CalloutBubbleProps {
  text: string;
  startFrame: number;
  /** Position from right edge in px */
  right: number;
  /** Position from top in px */
  top: number;
}

/**
 * Callout bubble that slides in from the right with an arrow.
 */
const CalloutBubble: React.FC<CalloutBubbleProps> = ({
  text,
  startFrame,
  right,
  top,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [startFrame, startFrame + 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateX = interpolate(
    frame,
    [startFrame, startFrame + 18],
    [60, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        position: "absolute",
        right,
        top,
        opacity,
        transform: `translateX(${translateX}px)`,
        display: "flex",
        alignItems: "center",
        gap: 0,
        zIndex: 10,
      }}
    >
      {/* Arrow pointing left */}
      <div
        style={{
          width: 0,
          height: 0,
          borderTop: "10px solid transparent",
          borderBottom: "10px solid transparent",
          borderRight: `14px solid ${COLORS.ink}`,
        }}
      />
      <div
        style={{
          background: COLORS.ink,
          color: COLORS.paper,
          padding: "10px 18px",
          borderRadius: 6,
          fontFamily: FONTS.heading,
          fontSize: 22,
          fontStyle: "italic",
          fontWeight: 400,
          letterSpacing: "-0.01em",
          whiteSpace: "nowrap" as const,
          boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
        }}
      >
        {text}
        {/* Amber underline */}
        <div
          style={{
            height: 2,
            width: "100%",
            background: COLORS.accent,
            borderRadius: 1,
            marginTop: 4,
          }}
        />
      </div>
    </div>
  );
};

/**
 * DashboardScene: 30–50s (frames 900–1500 in main comp, 0–600 inside this sequence).
 *
 * - Full-width dashboard recording
 * - Three callout bubbles slide in from the right at staggered times
 * - Subtle zoom-in effect on the video as the scene progresses
 */
export const DashboardScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Scene fade in
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scene fade out
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const combinedOpacity = Math.min(opacity, fadeOut);

  // Subtle zoom: 1.0 → 1.04 over the full scene
  const videoScale = interpolate(frame, [0, durationInFrames], [1, 1.04], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Callout timings (relative to this scene):
  // "Forbrug per udvalg"             → 35s = 5s into scene = frame 150
  // "Filtrér på dato og kategori"    → 40s = 10s into scene = frame 300
  // "Godkend og udbetal med ét klik" → 45s = 15s into scene = frame 450
  const CALLOUT_1_START = 150;
  const CALLOUT_2_START = 300;
  const CALLOUT_3_START = 450;

  return (
    <AbsoluteFill
      style={{
        background: COLORS.ink,
        opacity: combinedOpacity,
      }}
    >
      {/* Full-width video */}
      <AbsoluteFill
        style={{
          transform: `scale(${videoScale})`,
          transformOrigin: "center center",
        }}
      >
        <OffthreadVideo
          src={staticFile("dashboard-capture.webm")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "top center",
          }}
        />
      </AbsoluteFill>

      {/* Dark overlay for readability of callouts */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to left, rgba(26,22,18,0.35) 0%, transparent 50%)",
          pointerEvents: "none",
        }}
      />

      {/* Callout bubbles */}
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <CalloutBubble
          text="Forbrug per udvalg"
          startFrame={CALLOUT_1_START}
          right={40}
          top={200}
        />
        <CalloutBubble
          text="Filtrér på dato og kategori"
          startFrame={CALLOUT_2_START}
          right={40}
          top={380}
        />
        <CalloutBubble
          text="Godkend og udbetal med ét klik"
          startFrame={CALLOUT_3_START}
          right={40}
          top={560}
        />
      </AbsoluteFill>

      {/* Top label */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 48,
          opacity: interpolate(frame, [20, 40], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <span
          style={{
            fontFamily: FONTS.body,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase" as const,
            color: COLORS.accent,
            background: "rgba(26,22,18,0.7)",
            padding: "4px 10px",
            borderRadius: 4,
          }}
        >
          Dashboard
        </span>
      </div>
    </AbsoluteFill>
  );
};
