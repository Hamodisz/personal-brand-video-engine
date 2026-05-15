import React from "react";
import { AbsoluteFill, interpolate, spring, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

interface StatCalloutProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  stat: string;
  statLabel: string;
  sub?: string;
}

export const StatCallout: React.FC<StatCalloutProps> = ({
  frame, shotStartFrame, shotEndFrame, stat, statLabel, sub,
}) => {
  const { fps } = useVideoConfig();
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const shotOp = interpolate(localFrame, [0, 10, shotLen - 8, shotLen], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const statSpring = spring({ frame: localFrame, fps, config: { damping: 12, stiffness: 160 } });
  const statScale = interpolate(statSpring, [0, 1], [0.3, 1.0]);
  const statOp = interpolate(localFrame, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  const labelOp = interpolate(localFrame, [15, 28], [0, 1], { extrapolateRight: "clamp" });
  const labelY = interpolate(localFrame, [15, 28], [20, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity: shotOp }}>
      <AbsoluteFill style={{ background: "#06060f" }} />
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 55% 45% at 50% 45%, rgba(108,99,255,0.12) 0%, transparent 100%)",
        }}
      />

      {/* Centered stat block */}
      <AbsoluteFill
        style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          paddingBottom: 80,
        }}
      >
        <div
          style={{
            fontSize: 160,
            fontWeight: 900,
            fontFamily: "sans-serif",
            color: "#A78BFA",
            lineHeight: 1.0,
            letterSpacing: -4,
            transform: `scale(${statScale})`,
            opacity: statOp,
            textShadow: "0 0 80px rgba(167,139,250,0.4)",
          }}
        >
          {stat}
        </div>
        <div
          style={{
            fontSize: 38,
            fontWeight: 800,
            fontFamily: "sans-serif",
            color: "#ffffff",
            marginTop: 16,
            letterSpacing: -0.5,
            opacity: labelOp,
            transform: `translateY(${labelY}px)`,
          }}
        >
          {statLabel}
        </div>
        {sub && (
          <div
            style={{
              fontSize: 22,
              fontWeight: 500,
              fontFamily: "sans-serif",
              color: "rgba(255,255,255,0.5)",
              marginTop: 10,
              opacity: labelOp,
            }}
          >
            {sub}
          </div>
        )}
      </AbsoluteFill>

      {/* Body faint behind */}
      <AbsoluteFill style={{ display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
        <OffthreadVideo
          src={staticFile("body_cutout.webm")}
          style={{
            height: "100%", width: "auto", objectFit: "contain",
            opacity: 0.15,
          }}
        />
      </AbsoluteFill>

      <AbsoluteFill style={{ background: "radial-gradient(ellipse 85% 88% at 50% 50%, transparent 38%, rgba(0,0,0,0.6) 100%)", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
