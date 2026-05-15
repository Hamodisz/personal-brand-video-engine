import React from "react";
import { AbsoluteFill, interpolate, Video, staticFile } from "remotion";

interface TalkingHeadProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
}

export const TalkingHead: React.FC<TalkingHeadProps> = ({ frame, shotStartFrame, shotEndFrame }) => {
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const opacity = interpolate(localFrame, [0, 12, shotLen - 8, shotLen], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#0a0a12", overflow: "hidden", opacity }}>
      {/* Gaming room - dark purple/blue gradient */}
      <AbsoluteFill style={{ 
        background: "linear-gradient(135deg, #1a0d2e 0%, #0d1a2e 50%, #0a0a15 100%)",
      }} />

      {/* Full-screen source video */}
      <AbsoluteFill>
        <Video
          src={staticFile("clip_clean.mp4")}
          style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(1.15) contrast(1.05)" }}
          volume={1}
        />
      </AbsoluteFill>

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 80% 85% at 50% 50%, transparent 38%, rgba(0,0,0,0.55) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
