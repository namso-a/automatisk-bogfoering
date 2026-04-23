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

const URL_TEXT = "kvitly.dk";
const CTA_TEXT = "Kom i gang på en e-mail";

/**
 * OutroScene: 50–60s (frames 1500–1800 in main comp, 0–300 inside this sequence).
 *
 * - Fade to off-white
 * - Logo appears centered (spring)
 * - URL "kvitly.dk" types in
 * - CTA tagline fades in
 * - Amber accent line animates 0→100%
 */
export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade in from black/ink
  const bgOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Logo spring entrance
  const logoScale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 16, stiffness: 140, mass: 0.7 },
    durationInFrames: 35,
  });
  const logoOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // URL typing — starts at frame 50
  const URL_START = 50;
  const CHAR_DELAY = 5;
  const urlCharsVisible = Math.floor((frame - URL_START) / CHAR_DELAY) + 1;
  const visibleUrl = URL_TEXT.slice(0, Math.max(0, urlCharsVisible));
  const urlCursorVisible =
    visibleUrl.length < URL_TEXT.length
      ? Math.floor(frame / 8) % 2 === 0
      : false;

  // CTA fade in after URL finishes
  const ctaStart = URL_START + URL_TEXT.length * CHAR_DELAY + 15;
  const ctaOpacity = interpolate(frame, [ctaStart, ctaStart + 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const ctaY = interpolate(frame, [ctaStart, ctaStart + 25], [12, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Amber line — grows after CTA
  const lineStart = ctaStart + 30;
  const lineWidth = interpolate(frame, [lineStart, lineStart + 40], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtle glow pulse tied to the logo
  const glowOpacity = interpolate(frame, [35, 70], [0, 0.35], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Final hold — no fade out (video ends here)
  const sceneOpacity = interpolate(frame, [0, 15], [0, 1], {
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
      {/* Off-white background fading in */}
      <AbsoluteFill
        style={{
          background: COLORS.paper,
          opacity: bgOpacity,
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 32,
        }}
      >
        {/* Amber glow */}
        <div
          style={{
            position: "absolute",
            width: 400,
            height: 400,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${COLORS.accent}55 0%, transparent 70%)`,
            opacity: glowOpacity,
          }}
        />

        {/* Logo + wordmark */}
        <div
          style={{
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
            position: "relative",
            zIndex: 1,
          }}
        >
          <KvitlyLogo markSize={100} wordmarkSize={80} inline={false} />
        </div>

        {/* Typed URL */}
        <div
          style={{
            position: "relative",
            zIndex: 1,
            opacity: interpolate(frame, [URL_START, URL_START + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <span
            style={{
              fontFamily: FONTS.body,
              fontSize: 42,
              fontWeight: 500,
              letterSpacing: "0.02em",
              color: COLORS.accent,
            }}
          >
            {visibleUrl}
            {urlCursorVisible && (
              <span
                style={{
                  display: "inline-block",
                  width: "0.06em",
                  height: "0.85em",
                  background: COLORS.accent,
                  verticalAlign: "middle",
                  marginLeft: 3,
                }}
              />
            )}
          </span>
        </div>

        {/* CTA tagline */}
        <div
          style={{
            opacity: ctaOpacity,
            transform: `translateY(${ctaY}px)`,
            position: "relative",
            zIndex: 1,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONTS.heading,
              fontSize: 30,
              fontStyle: "italic",
              fontWeight: 300,
              color: COLORS.muted,
              letterSpacing: "-0.01em",
            }}
          >
            {CTA_TEXT}
          </span>
        </div>

        {/* Amber accent line */}
        <div
          style={{
            position: "relative",
            zIndex: 1,
            width: 480,
            height: 3,
            background: COLORS.warmDark,
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              height: "100%",
              width: `${lineWidth}%`,
              background: COLORS.accent,
              borderRadius: 2,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
