import React from "react";
import { COLORS, FONTS } from "../theme";

interface KvitlyLogoProps {
  /** Width of the mark SVG in pixels */
  markSize?: number;
  /** Font size for the wordmark. If 0, wordmark is hidden. */
  wordmarkSize?: number;
  /** Show the wordmark inline next to the mark */
  inline?: boolean;
  /** Overall opacity (for fade animations) */
  opacity?: number;
}

/**
 * Reusable Kvitly brand mark + wordmark.
 * The SVG is the receipt shape with zigzag bottom and amber bottom line,
 * exactly matching the favicon used in form.html.
 */
export const KvitlyLogo: React.FC<KvitlyLogoProps> = ({
  markSize = 48,
  wordmarkSize = 48,
  inline = false,
  opacity = 1,
}) => {
  const aspectRatio = 24 / 30; // viewBox 24×30
  const markWidth = markSize * aspectRatio;
  const markHeight = markSize;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: inline ? "row" : "column",
        alignItems: "center",
        gap: inline ? markSize * 0.3 : markSize * 0.2,
        opacity,
      }}
    >
      {/* Receipt mark */}
      <svg
        viewBox="0 0 24 30"
        width={markWidth}
        height={markHeight}
        style={{ flexShrink: 0 }}
      >
        {/* Receipt body + zigzag bottom */}
        <path
          d="M3 2 L21 2 L21 25 L19 27 L17 25 L15 27 L13 25 L11 27 L9 25 L7 27 L5 25 L3 27 Z"
          fill={COLORS.ink}
        />
        {/* Lines on receipt — white */}
        <rect x="6" y="7" width="12" height="1.6" fill={COLORS.paper} />
        <rect x="6" y="11" width="9" height="1.6" fill={COLORS.paper} />
        <rect x="6" y="15" width="12" height="1.6" fill={COLORS.paper} />
        {/* Amber bottom line */}
        <rect x="6" y="19.5" width="12" height="2.4" fill={COLORS.accent} />
      </svg>

      {/* Wordmark */}
      {wordmarkSize > 0 && (
        <span
          style={{
            fontFamily: FONTS.heading,
            fontSize: wordmarkSize,
            fontWeight: 400,
            letterSpacing: "-0.02em",
            color: COLORS.ink,
            lineHeight: 1,
          }}
        >
          Kvitly
        </span>
      )}
    </div>
  );
};
