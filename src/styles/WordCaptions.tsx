import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { createTikTokStyleCaptions } from "@remotion/captions";

interface Caption {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
}

interface WordCaptionsProps {
  captions: Caption[];
  position?: "top" | "bottom" | "center";
}

export const WordCaptions: React.FC<WordCaptionsProps> = ({
  captions,
  position = "bottom",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentMs = (frame / fps) * 1000;

  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: 800,
  });

  const activePage = pages.findIndex((page) => {
    const tokens = page.tokens;
    if (!tokens.length) return false;
    const pageStart = tokens[0].fromMs;
    const pageEnd = tokens[tokens.length - 1].toMs;
    return currentMs >= pageStart && currentMs <= pageEnd + 400;
  });

  if (activePage === -1) return null;

  const page = pages[activePage];

  const positionStyle: React.CSSProperties =
    position === "bottom"
      ? { bottom: 160 }
      : position === "top"
      ? { top: 140 }
      : { top: "50%", transform: "translateY(-50%)" };

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        gap: "0 10px",
        padding: "0 48px",
        direction: "rtl",
        ...positionStyle,
      }}
    >
      {page.tokens.map((token, i) => {
        const isActive = currentMs >= token.fromMs && currentMs <= token.toMs;
        const hasShown = currentMs > token.fromMs;

        const wordFrame = Math.max(
          0,
          frame - Math.round((token.fromMs / 1000) * fps)
        );
        const sc = spring({
          frame: wordFrame,
          fps,
          config: { damping: 14, stiffness: 200, mass: 0.6 },
        });
        const scale = interpolate(sc, [0, 1], [0.75, 1]);

        return (
          <span
            key={i}
            style={{
              fontFamily: "'Cairo', 'Helvetica Neue', sans-serif",
              fontSize: 68,
              fontWeight: 900,
              lineHeight: 1.25,
              color: isActive ? "#FFDE59" : "#FFFFFF",
              textShadow: isActive
                ? "0 0 24px rgba(255,222,89,0.55), 2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000"
                : "2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000",
              transform: `scale(${scale})`,
              opacity: hasShown ? 1 : 0,
              display: "inline-block",
              whiteSpace: "pre",
              transition: "color 0.05s ease",
            }}
          >
            {token.text}
          </span>
        );
      })}
    </div>
  );
};
