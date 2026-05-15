import React from "react";
import { AbsoluteFill, interpolate, spring, OffthreadVideo, Img, staticFile, useVideoConfig } from "remotion";

interface WebsiteOverlayProps {
  frame: number;
  shotStartFrame: number;
  shotEndFrame: number;
  websiteAsset?: string;
}

export const WebsiteOverlay: React.FC<WebsiteOverlayProps> = ({
  frame, shotStartFrame, shotEndFrame, websiteAsset = "site_hero.png",
}) => {
  const { fps } = useVideoConfig();
  const localFrame = frame - shotStartFrame;
  const shotLen = shotEndFrame - shotStartFrame;

  const shotOpacity = interpolate(localFrame, [0, 12, shotLen - 8, shotLen], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const websiteSpring = spring({ frame: localFrame, fps, config: { damping: 24, stiffness: 100 } });
  const websiteX = interpolate(websiteSpring, [0, 1], [-580, 0]);

  const bodySpring = spring({ frame: localFrame, fps, config: { damping: 22, stiffness: 110 } });
  const bodyScale = interpolate(bodySpring, [0, 1], [1.0, 0.48]);

  const dividerH = interpolate(localFrame, [8, 28], [0, 1920], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: shotOpacity, background: "#06060f" }}>
      {/* Website panel — left 52%, slides in */}
      <div
        style={{
          position: "absolute",
          left: 0, top: 0, bottom: 0,
          width: "52%",
          transform: `translateX(${websiteX}px)`,
          overflow: "hidden",
        }}
      >
        <Img
          src={staticFile(websiteAsset)}
          style={{
            width: "100%", height: "100%",
            objectFit: "cover", objectPosition: "top center",
            filter: "brightness(0.82) saturate(1.15)",
          }}
        />
        {/* Dark tint — readable, NO blur */}
        <AbsoluteFill style={{ background: "rgba(6,4,20,0.28)" }} />
        {/* Right edge feather */}
        <AbsoluteFill
          style={{
            background: "linear-gradient(90deg, rgba(0,0,0,0.1) 0%, transparent 15%, transparent 65%, rgba(6,4,20,0.85) 100%)",
          }}
        />
      </div>

      {/* Purple vertical divider */}
      <svg
        style={{ position: "absolute", left: "52%", top: 0, width: 4, height: "100%", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="div-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6c63ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="3" height={dividerH} fill="url(#div-grad)"
          style={{ filter: "drop-shadow(0 0 8px rgba(108,99,255,0.7))" }} />
      </svg>

      {/* Body — right side, shrinks */}
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
            marginRight: -30,
          }}
        />
      </AbsoluteFill>

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 90% 88% at 50% 50%, transparent 40%, rgba(0,0,0,0.5) 100%)",
          pointerEvents: "none",
        }}
      />
      {/* Bottom burn */}
      <AbsoluteFill
        style={{
          background: "linear-gradient(0deg, rgba(6,4,20,0.85) 0%, transparent 18%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
