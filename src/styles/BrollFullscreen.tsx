import React from "react";
import { AbsoluteFill, interpolate, OffthreadVideo } from "remotion";

interface BrollFullscreenProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  brollFile: string;
  brollLoop?: boolean;
  transitionOut?: string;
}

export const BrollFullscreen: React.FC<BrollFullscreenProps> = ({
  frame, shotStartFrame, shotEndFrame, brollFile, brollLoop = false, transitionOut = "cut",
}) => {
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  // Fade in 12 frames, hard cut out (unless crossfade)
  const fadeOutFrames = transitionOut === "crossfade_8" ? 8 : transitionOut === "dip_black_10" ? 10 : 0;
  const fadeInEnd = Math.min(12, shotLen - 1);
  const fadeOutStart = Math.max(fadeInEnd + 1, shotLen - fadeOutFrames);
  const opacity = fadeOutFrames > 0
    ? interpolate(localFrame, [0, fadeInEnd, fadeOutStart, shotLen], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : interpolate(localFrame, [0, fadeInEnd], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity }}>
      {/* B-roll */}
      <OffthreadVideo
        src={brollFile}
        loop={brollLoop}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />

      {/* Dark tint to keep captions readable */}
      <AbsoluteFill style={{ background: "rgba(0,0,0,0.25)" }} />

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 85% 88% at 50% 50%, transparent 35%, rgba(0,0,0,0.6) 100%)",
          pointerEvents: "none",
        }}
      />
      {/* Bottom burn for captions */}
      <AbsoluteFill
        style={{
          background: "linear-gradient(0deg, rgba(0,0,0,0.7) 0%, transparent 22%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
