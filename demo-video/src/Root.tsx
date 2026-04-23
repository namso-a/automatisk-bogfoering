import React from "react";
import { Composition } from "remotion";
import { KvitlyComposition } from "./Composition";
import { FPS, TOTAL_FRAMES, GOOGLE_FONTS_URL } from "./theme";

/**
 * Root.tsx — Remotion composition registry.
 *
 * Registers the main KvitlyDemo composition (60s, 30fps, 1920×1080).
 * Also registers a KvitlyShort composition for a 30-second cut (frames 0–900).
 *
 * Fonts are loaded via a standard <link> tag injected into the document head.
 * Remotion bundles this as part of the preview/render environment.
 */

// Inject Google Fonts into the document head at composition load time
if (typeof document !== "undefined") {
  const existing = document.querySelector(`link[data-kvitly-fonts]`);
  if (!existing) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = GOOGLE_FONTS_URL;
    link.setAttribute("data-kvitly-fonts", "true");
    document.head.appendChild(link);
  }
}

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Full 60-second demo */}
      <Composition
        id="KvitlyDemo"
        component={KvitlyComposition}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{}}
      />

      {/* 30-second short version (title + problem + upload only, frames 0–900) */}
      <Composition
        id="KvitlyShort"
        component={KvitlyComposition}
        durationInFrames={900}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
