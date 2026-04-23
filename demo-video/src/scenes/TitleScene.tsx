import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { KvitlyLogo } from "../components/KvitlyLogo";
import { COLORS, FONTS } from "../theme";

const TAGLINE = "Digital kasserermappe til foreninger";

/**
 * TitleScene: 0–5s (frames 0–150)
 *
 * - Fades in from black
 * - Logo mark scales + fades in (spring animation)
 * - Wordmark types in letter by letter
 * - Tagline fades in below
 * - Subtle amber glow around the mark
 */
export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Background fade from black to paper
  const bgOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Logo mark spring entrance
  const logoScale = spring({
    frame: frame - 10,
    fps,
    config: { damping: 14, stiffness: 120, mass: 0.8 },
    durationInFrames: 40,
  });
  const logoOpacity = interpolate(frame, [10, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Wordmark: reveal characters one by one
  // Each character takes ~3 frames to appear; starts at frame 35
  const CHARS_START = 35;
  const CHAR_DELAY = 4;
  const wordmark = "Kvitly";
  const charsVisible = Math.floor((frame - CHARS_START) / CHAR_DELAY) + 1;
  const visibleWord = wordmark.slice(0, Math.max(0, charsVisible));

  // Blinking cursor
  const cursorVisible =
    visibleWord.length < wordmark.length
      ? Math.floor(frame / 8) % 2 === 0
      : false;

  // Tagline fade in after wordmark finishes
  const taglineStart = CHARS_START + wordmark.length * CHAR_DELAY + 10;
  const taglineOpacity = interpolate(
    frame,
    [taglineStart, taglineStart + 25],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const taglineTranslateY = interpolate(
    frame,
    [taglineStart, taglineStart + 25],
    [12, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Amber glow pulse
  const glowOpacity = interpolate(frame, [50, 90], [0, 0.4], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scene fade-out at the end (last 15 frames)
  const sceneOpacity = interpolate(frame, [135, 150], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.ink,
        opacity: sceneOpacity,
      }}
    >
      {/* Paper background fading in */}
      <AbsoluteFill
        style={{
          background: COLORS.paper,
          opacity: bgOpacity,
        }}
      />

      {/* Center content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 32,
        }}
      >
        {/* Amber glow behind mark */}
        <div
          style={{
            position: "absolute",
            width: 300,
            height: 300,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${COLORS.accent}55 0%, transparent 70%)`,
            opacity: glowOpacity,
          }}
        />

        {/* Logo mark only (no wordmark — we type it separately) */}
        <div
          style={{
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
            position: "relative",
            zIndex: 1,
          }}
        >
          <KvitlyLogo markSize={120} wordmarkSize={0} />
        </div>

        {/* Typed wordmark */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <span
            style={{
              fontFamily: FONTS.heading,
              fontSize: 96,
              fontWeight: 300,
              letterSpacing: "-0.04em",
              color: COLORS.ink,
              lineHeight: 1,
            }}
          >
            {visibleWord}
            {cursorVisible && (
              <span
                style={{
                  display: "inline-block",
                  width: "0.06em",
                  height: "0.9em",
                  background: COLORS.accent,
                  verticalAlign: "middle",
                  marginLeft: 4,
                }}
              />
            )}
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            opacity: taglineOpacity,
            transform: `translateY(${taglineTranslateY}px)`,
            position: "relative",
            zIndex: 1,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONTS.body,
              fontSize: 24,
              fontWeight: 400,
              color: COLORS.muted,
              letterSpacing: "0.02em",
            }}
          >
            {TAGLINE}
          </span>
          {/* Amber accent line */}
          <div
            style={{
              marginTop: 12,
              height: 2,
              width: "100%",
              background: COLORS.accent,
              borderRadius: 1,
              opacity: taglineOpacity,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
