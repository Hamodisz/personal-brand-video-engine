import React from "react";
import { AbsoluteFill, interpolate, spring, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

interface CtaCloserProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  ctaText: string;
  url: string;
}

export const CtaCloser: React.FC<CtaCloserProps> = ({
  frame, shotStartFrame, shotEndFrame, ctaText, url,
}) => {
  const { fps } = useVideoConfig();
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const shotOp = interpolate(localFrame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  const pillSpring = spring({ frame: localFrame, fps, config: { damping: 14, stiffness: 110 } });
  const pillScale = interpolate(pillSpring, [0, 1], [0.6, 1.0]);

  const urlChars = Math.floor(interpolate(localFrame, [25, 65], [0, url.length], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  }));
  const cursorOn = Math.floor(localFrame / 9) % 2 === 0;

  const btnGlow = 40 + 18 * Math.sin(localFrame * 0.14);

  return (
    <AbsoluteFill style={{ opacity: shotOp }}>
      <AbsoluteFill style={{ background: "#06060f" }} />
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 65% 55% at 50% 55%, rgba(108,99,255,0.14) 0%, rgba(168,85,247,0.06) 60%, transparent 100%)",
        }}
      />

      {/* Body faint */}
      <AbsoluteFill style={{ display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
        <OffthreadVideo
          src={staticFile("body_cutout.webm")}
          style={{ height: "100%", width: "auto", objectFit: "contain", opacity: 0.2 }}
        />
      </AbsoluteFill>

      {/* CTA pill + URL */}
      <AbsoluteFill
        style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end",
          paddingBottom: 160,
        }}
      >
        {/* URL typewriter */}
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 22,
            color: "rgba(168,85,247,0.85)",
            letterSpacing: 1.5,
            marginBottom: 20,
          }}
        >
          {url.slice(0, urlChars)}{cursorOn && urlChars < url.length ? "▋" : ""}
        </div>

        {/* CTA Pill */}
        <div
          style={{
            background: "linear-gradient(135deg, #6c63ff 0%, #a855f7 100%)",
            borderRadius: 100,
            padding: "22px 64px",
            fontSize: 32,
            fontWeight: 800,
            fontFamily: "sans-serif",
            color: "#ffffff",
            letterSpacing: -0.3,
            transform: `scale(${pillScale})`,
            boxShadow: `0 0 ${btnGlow}px rgba(108,99,255,0.65), 0 0 120px rgba(168,85,247,0.2)`,
          }}
        >
          {ctaText}
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{ background: "radial-gradient(ellipse 85% 88% at 50% 50%, transparent 38%, rgba(0,0,0,0.55) 100%)", pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};
