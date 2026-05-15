import React from "react";
import { AbsoluteFill, interpolate, spring, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

interface Card {
  eyebrow: string;
  headline: string;
  sub?: string;
}

interface TextCardsProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  cards: Card[];
}

const CARD_STAGGER = 45; // frames between cards

export const TextCards: React.FC<TextCardsProps> = ({ frame, shotStartFrame, shotEndFrame, cards }) => {
  const { fps } = useVideoConfig();
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const opacity = interpolate(localFrame, [0, 10, shotLen - 8, shotLen], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const cardTops = [480, 800, 1120];

  return (
    <AbsoluteFill style={{ opacity }}>
      {/* Dark bg with subtle gradient */}
      <AbsoluteFill style={{ background: "#06060f" }} />
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 60% 50% at 15% 50%, rgba(108,99,255,0.05) 0%, transparent 100%)",
        }}
      />

      {/* Body — small, right side, always visible */}
      <AbsoluteFill
        style={{ display: "flex", alignItems: "flex-end", justifyContent: "flex-end" }}
      >
        <OffthreadVideo
          src={staticFile("body_cutout.webm")}
          style={{
            height: "100%", width: "auto", objectFit: "contain",
            transform: "scale(0.42)",
            transformOrigin: "bottom right",
            opacity: 0.55,
            marginRight: -20,
          }}
        />
      </AbsoluteFill>

      {/* Cards */}
      {cards.slice(0, 3).map((card, i) => {
        const cardStart = i * CARD_STAGGER;
        const cardFrame = Math.max(0, localFrame - cardStart);
        const cardSpring = spring({ frame: cardFrame, fps, config: { damping: 22, stiffness: 140 } });
        const cardX = interpolate(cardSpring, [0, 1], [-100, 0]);
        const cardOp = interpolate(cardFrame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
        const accentW = interpolate(cardFrame, [6, 28], [0, 520], { extrapolateRight: "clamp" });

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 40,
              right: 40,
              top: cardTops[i] ?? 480 + i * 320,
              borderRadius: 20,
              padding: "28px 36px",
              background: "rgba(8,6,24,0.88)",
              border: "1px solid rgba(108,99,255,0.28)",
              backdropFilter: "blur(12px)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
              transform: `translateX(${cardX}px)`,
              opacity: cardOp,
              overflow: "hidden",
            }}
          >
            {/* Accent line */}
            <div
              style={{
                position: "absolute",
                top: 0, left: 0,
                height: 2,
                width: accentW,
                background: "linear-gradient(90deg, #6c63ff, #a855f7)",
                boxShadow: "0 0 8px rgba(108,99,255,0.8)",
              }}
            />
            <div style={{ color: "rgba(168,85,247,0.9)", fontSize: 22, fontWeight: 700, fontFamily: "sans-serif", letterSpacing: 3, textTransform: "uppercase", marginBottom: 14 }}>
              {card.eyebrow}
            </div>
            <div style={{ color: "#ffffff", fontSize: 48, fontWeight: 900, fontFamily: "sans-serif", lineHeight: 1.2, marginBottom: 12, direction: "rtl" }}>
              {card.headline}
            </div>
            {card.sub && (
              <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 28, fontWeight: 500, fontFamily: "sans-serif", direction: "rtl" }}>
                {card.sub}
              </div>
            )}
          </div>
        );
      })}

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 88% 90% at 50% 50%, transparent 40%, rgba(0,0,0,0.5) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
