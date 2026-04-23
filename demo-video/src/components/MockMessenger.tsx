import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../theme";

/** Chaotic receipt filenames that will stack into the chat */
const RECEIPT_MESSAGES = [
  { filename: "IMG_0293.jpg", sender: "Maja T.", time: "10:34" },
  { filename: "scan (2).pdf", sender: "Lars B.", time: "10:41" },
  { filename: "Foto 14-03-2024.jpg", sender: "Sofie K.", time: "11:02" },
  { filename: "kvittering_FINAL.jpeg", sender: "Anders M.", time: "11:58" },
  { filename: "IMG_20240315_084512.jpg", sender: "Nadia P.", time: "14:22" },
] as const;

/**
 * Mock Messenger-style chat window showing receipt chaos.
 * Each message card animates in with a slight rotation for organic feel.
 * Rendered over the ProblemScene time window (frames 150–450 relative to comp start).
 */
export const MockMessenger: React.FC = () => {
  const frame = useCurrentFrame();

  // Each card appears every 40 frames (≈1.3s)
  const STAGGER = 40;
  // Base start frame within the scene (problem scene starts at 150 in main comp,
  // but Remotion sequences offset this automatically)
  const BASE_DELAY = 20;

  return (
    <div
      style={{
        width: 340,
        background: COLORS.white,
        borderRadius: 16,
        boxShadow: "0 8px 40px rgba(26,22,18,0.18)",
        overflow: "hidden",
        fontFamily: FONTS.body,
      }}
    >
      {/* Messenger header */}
      <div
        style={{
          background: "#1877f2",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
          }}
        >
          👥
        </div>
        <div>
          <div style={{ color: "#fff", fontWeight: 600, fontSize: 14 }}>
            Fredens Ungdom — Kasserer
          </div>
          <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 12 }}>
            8 deltagere
          </div>
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          padding: "12px 12px 8px",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          minHeight: 300,
          background: "#f0f2f5",
        }}
      >
        {RECEIPT_MESSAGES.map((msg, i) => {
          const appearFrame = BASE_DELAY + i * STAGGER;
          const opacity = interpolate(
            frame,
            [appearFrame, appearFrame + 12],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          const translateY = interpolate(
            frame,
            [appearFrame, appearFrame + 12],
            [20, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          // Slight random-looking rotation per card (deterministic via index)
          const rotations = [-1.5, 0.8, -0.5, 1.2, -0.9];
          const rotation = rotations[i % rotations.length] ?? 0;

          return (
            <div
              key={msg.filename}
              style={{
                opacity,
                transform: `translateY(${translateY}px) rotate(${rotation}deg)`,
                display: "flex",
                flexDirection: "column",
                alignSelf: i % 2 === 0 ? "flex-start" : "flex-end",
                maxWidth: "80%",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: COLORS.muted,
                  marginBottom: 3,
                  paddingLeft: 4,
                }}
              >
                {msg.sender} · {msg.time}
              </div>
              {/* Receipt file card */}
              <div
                style={{
                  background: COLORS.white,
                  borderRadius: 10,
                  padding: "10px 12px",
                  boxShadow: "0 1px 4px rgba(0,0,0,0.12)",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                {/* File icon */}
                <div
                  style={{
                    width: 36,
                    height: 44,
                    borderRadius: 4,
                    background: COLORS.warm,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    position: "relative",
                  }}
                >
                  {/* Folded corner */}
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      right: 0,
                      width: 10,
                      height: 10,
                      background: COLORS.warmDark,
                      clipPath: "polygon(100% 0, 100% 100%, 0 100%)",
                    }}
                  />
                  <span style={{ fontSize: 14 }}>
                    {msg.filename.endsWith(".pdf") ? "📄" : "🖼️"}
                  </span>
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: COLORS.ink,
                      wordBreak: "break-all",
                    }}
                  >
                    {msg.filename}
                  </div>
                  <div style={{ fontSize: 11, color: COLORS.muted }}>
                    {msg.filename.endsWith(".pdf") ? "PDF" : "Billede"} ·{" "}
                    {(Math.random() * 2 + 0.5).toFixed(1)} MB
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom bar */}
      <div
        style={{
          padding: "8px 12px",
          background: COLORS.white,
          borderTop: `1px solid ${COLORS.warm}`,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            flex: 1,
            background: "#f0f2f5",
            borderRadius: 20,
            padding: "8px 14px",
            fontSize: 13,
            color: COLORS.muted,
          }}
        >
          Aa
        </div>
        <span style={{ fontSize: 20 }}>👍</span>
      </div>
    </div>
  );
};
