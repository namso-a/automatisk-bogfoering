import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { MockMessenger } from "../components/MockMessenger";
import { COLORS, FONTS } from "../theme";

/**
 * ProblemScene: 5–15s (frames 150–450 in main comp, 0–300 inside this sequence).
 *
 * - Title at top: "Kvitteringskaos i foreningen"
 * - Animated mock Messenger chat with receipt chaos stacking up
 * - Subtitle about manual tracking pain
 */
export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Fade in from previous scene
  const sceneOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade out at end
  const fadeOut = interpolate(frame, [280, 300], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const combinedOpacity = Math.min(sceneOpacity, fadeOut);

  // Title slide in from top
  const titleY = interpolate(frame, [0, 25], [-40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Messenger panel slide in from right
  const messengerX = interpolate(frame, [15, 50], [200, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const messengerOpacity = interpolate(frame, [15, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pain-point label
  const labelOpacity = interpolate(frame, [180, 210], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const labelY = interpolate(frame, [180, 210], [16, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.paper,
        opacity: combinedOpacity,
      }}
    >
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "60px 80px",
          gap: 48,
        }}
      >
        {/* Title */}
        <div
          style={{
            transform: `translateY(${titleY}px)`,
            textAlign: "center",
          }}
        >
          <h1
            style={{
              fontFamily: FONTS.heading,
              fontSize: 64,
              fontWeight: 400,
              letterSpacing: "-0.03em",
              color: COLORS.ink,
              lineHeight: 1.1,
            }}
          >
            Kvitteringskaos{" "}
            <em
              style={{
                fontStyle: "italic",
                color: COLORS.accent,
              }}
            >
              i foreningen
            </em>
          </h1>
        </div>

        {/* Main content: messenger + labels side by side */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 60,
            width: "100%",
            maxWidth: 1000,
            justifyContent: "center",
          }}
        >
          {/* Messenger panel */}
          <div
            style={{
              transform: `translateX(${messengerX}px)`,
              opacity: messengerOpacity,
              flexShrink: 0,
            }}
          >
            <MockMessenger />
          </div>

          {/* Pain-point labels */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 28,
              paddingTop: 40,
            }}
          >
            {[
              { icon: "🗂️", text: "Svært at finde kvitteringerne" },
              { icon: "🔢", text: "Manuel summering i Excel" },
              { icon: "😓", text: "Kassereren jager stadig folk" },
              { icon: "📷", text: "Dårlig billedkvalitet, forkert beløb" },
            ].map((item, i) => {
              const itemOpacity = interpolate(
                frame,
                [60 + i * 35, 80 + i * 35],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              const itemX = interpolate(
                frame,
                [60 + i * 35, 80 + i * 35],
                [-30, 0],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );

              return (
                <div
                  key={item.text}
                  style={{
                    opacity: itemOpacity,
                    transform: `translateX(${itemX}px)`,
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                  }}
                >
                  <span style={{ fontSize: 28 }}>{item.icon}</span>
                  <span
                    style={{
                      fontFamily: FONTS.body,
                      fontSize: 22,
                      color: COLORS.ink,
                      fontWeight: 500,
                    }}
                  >
                    {item.text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom label — "Der er en bedre måde" */}
        <div
          style={{
            opacity: labelOpacity,
            transform: `translateY(${labelY}px)`,
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONTS.heading,
              fontSize: 32,
              fontStyle: "italic",
              fontWeight: 300,
              color: COLORS.muted,
            }}
          >
            Der er en bedre måde.
          </span>
          <div
            style={{
              marginTop: 8,
              height: 2,
              width: 120,
              background: COLORS.accent,
              borderRadius: 1,
              margin: "8px auto 0",
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
