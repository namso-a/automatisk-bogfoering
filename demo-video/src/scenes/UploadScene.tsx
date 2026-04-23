import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TextCallout } from "../components/TextCallout";
import { COLORS, FONTS } from "../theme";

/**
 * UploadScene: 15–30s (frames 450–900 in main comp, 0–450 inside this sequence).
 *
 * Layout:
 * - Left half: Playwright form recording (form-capture.webm)
 * - Right half: three text callouts appearing in sync with the recording
 *
 * If the video file is missing (not yet captured), a placeholder is shown.
 */
export const UploadScene: React.FC = () => {
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

  // Divider line grows in
  const dividerHeight = interpolate(frame, [20, 50], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Callout start frames (relative to this scene)
  // "Frivillige uploader fra mobilen" → 15s mark = frame 0 in scene
  // "AI læser beløb, dato, butik"    → 20s mark = frame 150 in scene
  // "Vælger udvalg og indsender"      → 25s mark = frame 300 in scene
  const CALLOUT_1_START = 10;
  const CALLOUT_2_START = 160;
  const CALLOUT_3_START = 310;

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
          flexDirection: "row",
        }}
      >
        {/* Left half: form video recording */}
        <div
          style={{
            flex: 1,
            position: "relative",
            overflow: "hidden",
            background: COLORS.warm,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Browser chrome frame */}
          <div
            style={{
              width: "90%",
              height: "90%",
              borderRadius: 8,
              overflow: "hidden",
              boxShadow: "0 12px 48px rgba(26,22,18,0.2)",
              background: COLORS.white,
            }}
          >
            {/* Browser toolbar */}
            <div
              style={{
                background: "#f1f3f4",
                padding: "8px 12px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                borderBottom: "1px solid #ddd",
              }}
            >
              <div style={{ display: "flex", gap: 6 }}>
                {["#ff5f57", "#ffbd2e", "#28c840"].map((c) => (
                  <div
                    key={c}
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      background: c,
                    }}
                  />
                ))}
              </div>
              <div
                style={{
                  flex: 1,
                  background: "#fff",
                  borderRadius: 4,
                  padding: "4px 10px",
                  fontSize: 12,
                  color: COLORS.muted,
                  fontFamily: FONTS.body,
                  border: "1px solid #ddd",
                }}
              >
                localhost:5000
              </div>
            </div>

            {/* Video content */}
            <div
              style={{
                width: "100%",
                height: "calc(100% - 37px)",
                position: "relative",
              }}
            >
              <OffthreadVideo
                src={staticFile("form-capture.webm")}
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  objectPosition: "top center",
                }}
              />
            </div>
          </div>
        </div>

        {/* Vertical divider */}
        <div
          style={{
            width: 2,
            background: COLORS.warm,
            alignSelf: "center",
            height: `${dividerHeight}%`,
            transition: "none",
          }}
        />

        {/* Right half: text callouts */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "60px 64px",
            gap: 48,
          }}
        >
          {/* Section label */}
          <div>
            <span
              style={{
                fontFamily: FONTS.body,
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: "0.12em",
                textTransform: "uppercase" as const,
                color: COLORS.accent,
              }}
            >
              Indsendelse
            </span>
          </div>

          <TextCallout
            text="Frivillige uploader fra mobilen"
            startFrame={CALLOUT_1_START}
            italic={true}
            fontSize={36}
            showAccent={true}
          />

          <TextCallout
            text="AI læser beløb, dato, butik"
            startFrame={CALLOUT_2_START}
            italic={true}
            fontSize={36}
            showAccent={true}
          />

          <TextCallout
            text="Vælger udvalg og indsender"
            startFrame={CALLOUT_3_START}
            italic={true}
            fontSize={36}
            showAccent={true}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
