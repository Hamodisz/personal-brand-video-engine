import React from "react";
import { AbsoluteFill, interpolate, spring, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

interface PiPProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  brollFile: string;
  brollLoop?: boolean;
}

export const PiP: React.FC<PiPProps> = ({
  frame, shotStartFrame, shotEndFrame, brollFile, brollLoop = false,
}) => {
  const { fps } = useVideoConfig();
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const opacity = interpolate(localFrame, [0, 12, shotLen - 8, shotLen], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const bodySpring = spring({ frame: localFrame, fps, config: { damping: 20, stiffness: 120 } });
  const bodyScale = interpolate(bodySpring, [0, 1], [0, 0.38]);

  return (
    <AbsoluteFill style={{ opacity }}>
      {/* B-roll background (darkened) */}
      <OffthreadVideo
        src={brollFile}
        loop={brollLoop}
        style={{ width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.55) saturate(0.9)" }}
      />

      {/* Subtle color grade overlay */}
      <AbsoluteFill style={{ background: "rgba(6,4,20,0.35)" }} />

      {/* Body — small, bottom-right corner, springs in */}
      <AbsoluteFill
        style={{
          display: "flex", alignItems: "flex-end", justifyContent: "flex-end",
        }}
      >
        <OffthreadVideo
          src={staticFile("body_cutout.webm")}
          style={{
            height: "100%", width: "auto", objectFit: "contain",
            transform: `scale(${bodyScale})`,
            transformOrigin: "bottom right",
          }}
        />
      </AbsoluteFill>

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 88% 90% at 50% 50%, transparent 38%, rgba(0,0,0,0.55) 100%)",
          pointerEvents: "none",
        }}
      />
      <AbsoluteFill
        style={{
          background: "linear-gradient(0deg, rgba(0,0,0,0.65) 0%, transparent 20%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
