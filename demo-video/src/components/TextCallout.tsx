import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../theme";

interface TextCalloutProps {
  /** Text to display */
  text: string;
  /** Absolute frame at which this callout should begin fading in */
  startFrame: number;
  /** Duration of the fade-in in frames (default 20) */
  fadeFrames?: number;
  /** Whether to show the amber underline accent */
  showAccent?: boolean;
  /** Use italic Fraunces style */
  italic?: boolean;
  /** Font size in pixels */
  fontSize?: number;
  /** Optional inline style overrides for the container */
  style?: React.CSSProperties;
}

/**
 * Animated text callout with optional amber underline accent.
 * Fades in starting at `startFrame`. Stays visible until composition ends.
 */
export const TextCallout: React.FC<TextCalloutProps> = ({
  text,
  startFrame,
  fadeFrames = 20,
  showAccent = true,
  italic = true,
  fontSize = 28,
  style,
}) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [startFrame, startFrame + fadeFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const translateY = interpolate(
    frame,
    [startFrame, startFrame + fadeFrames],
    [16, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Accent line grows from 0→100% over fadeFrames after text appears
  const accentWidth = interpolate(
    frame,
    [startFrame + fadeFrames, startFrame + fadeFrames * 2],
    [0, 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        display: "inline-block",
        ...style,
      }}
    >
      <span
        style={{
          fontFamily: FONTS.heading,
          fontSize,
          fontWeight: 400,
          fontStyle: italic ? "italic" : "normal",
          color: COLORS.ink,
          letterSpacing: "-0.01em",
          lineHeight: 1.2,
        }}
      >
        {text}
      </span>

      {showAccent && (
        <div
          style={{
            marginTop: 6,
            height: 3,
            width: `${accentWidth}%`,
            background: COLORS.accent,
            borderRadius: 2,
          }}
        />
      )}
    </div>
  );
};
