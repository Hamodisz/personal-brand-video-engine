import React, { useState, useEffect } from "react";
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TalkingHead } from "./styles/TalkingHead";
import { WebsiteOverlay } from "./styles/WebsiteOverlay";
import { BrollFullscreen } from "./styles/BrollFullscreen";
import { PiP } from "./styles/PiP";
import { TextCards } from "./styles/TextCards";
import { StatCallout } from "./styles/StatCallout";
import { CtaCloser } from "./styles/CtaCloser";
import { WordCaptions } from "./styles/WordCaptions";

interface Caption {
  text: string;
  startMs: number;
  endMs: number;
  timestampMs: number | null;
  confidence: number | null;
}

interface Shot {
  id: number;
  style: string;
  start_s: number;
  end_s: number;
  transition_out?: string;
  // broll
  broll_file?: string;
  broll_loop?: boolean;
  // text_cards
  cards?: { eyebrow: string; headline: string; sub?: string }[];
  // stat_callout
  stat?: string;
  stat_label?: string;
  stat_sub?: string;
  // cta_closer
  cta_text?: string;
  url?: string;
  // website_overlay
  website_asset?: string;
}

interface ShotPlan {
  audio_source: string;
  duration_s: number;
  shots: Shot[];
}

// Film grain — unique id to avoid collisions with other compositions
const FilmGrain: React.FC<{ frame: number }> = ({ frame }) => {
  const seed = (frame * 6271) % 9999;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
        <defs>
          <filter id="fg-smart">
            <feTurbulence type="fractalNoise" baseFrequency="0.88" numOctaves="4" seed={seed} />
            <feColorMatrix type="saturate" values="0" />
          </filter>
        </defs>
        <rect width="100%" height="100%" filter="url(#fg-smart)" opacity="0.05" style={{ mixBlendMode: "screen" }} />
      </svg>
    </AbsoluteFill>
  );
};

export const SmartEdit: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [plan, setPlan] = useState<ShotPlan | null>(null);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [handle] = useState(() => delayRender("Loading shot plan + captions"));

  useEffect(() => {
    Promise.all([
      fetch(staticFile("shot_plan.json")).then(r => r.json()).catch(() => ({
        audio_source: "clip_clean.mp4",
        duration_s: 16.2,
        shots: [
          { id: 1, style: "talking_head", start_s: 0, end_s: 4 },
          { id: 2, style: "text_cards", start_s: 4, end_s: 11, cards: [{ eyebrow: "THE SYSTEM", headline: "AI Creative Director", sub: "7 styles. Full autopilot." }] },
          { id: 3, style: "website_overlay", start_s: 11, end_s: 14 },
          { id: 4, style: "cta_closer", start_s: 14, end_s: 16.2, cta_text: "Take the Free Quiz →", url: "sportsync.ai/quiz" },
        ],
      })),
      fetch(staticFile("captions.json")).then(r => r.json()).catch(() => []),
    ]).then(([planData, captionsData]: [ShotPlan, Caption[]]) => {
      setPlan(planData);
      setCaptions(captionsData);
      continueRender(handle);
    });
  }, []);

  if (!plan) return <AbsoluteFill style={{ background: "#06060f" }} />;

  const currentShot = plan.shots.find(s => {
    const sf = Math.floor(s.start_s * fps);
    const ef = Math.ceil(s.end_s * fps);
    return frame >= sf && frame < ef;
  });

  const renderShot = (shot: Shot) => {
    const sf = Math.floor(shot.start_s * fps);
    const ef = Math.ceil(shot.end_s * fps);

    switch (shot.style) {
      case "talking_head":
        return <TalkingHead frame={frame} shotStartFrame={sf} shotEndFrame={ef} />;
      case "website_overlay":
        return <WebsiteOverlay frame={frame} shotStartFrame={sf} shotEndFrame={ef} websiteAsset={shot.website_asset} />;
      case "broll_fullscreen":
        return <BrollFullscreen frame={frame} shotStartFrame={sf} shotEndFrame={ef} brollFile={staticFile(shot.broll_file ?? "")} brollLoop={shot.broll_loop} transitionOut={shot.transition_out} />;
      case "pip":
        return <PiP frame={frame} shotStartFrame={sf} shotEndFrame={ef} brollFile={staticFile(shot.broll_file ?? "")} brollLoop={shot.broll_loop} />;
      case "text_cards":
        return <TextCards frame={frame} shotStartFrame={sf} shotEndFrame={ef} cards={shot.cards ?? []} />;
      case "stat_callout":
        return <StatCallout frame={frame} shotStartFrame={sf} shotEndFrame={ef} stat={shot.stat ?? ""} statLabel={shot.stat_label ?? ""} sub={shot.stat_sub} />;
      case "cta_closer":
        return <CtaCloser frame={frame} shotStartFrame={sf} shotEndFrame={ef} ctaText={shot.cta_text ?? "Take the Free Quiz →"} url={shot.url ?? "sportsync.ai/quiz"} />;
      default:
        return <TalkingHead frame={frame} shotStartFrame={sf} shotEndFrame={ef} />;
    }
  };

  return (
    <AbsoluteFill>
      {/* Render all shots — each fades in/out in its window */}
      {plan.shots.map(shot => (
        <AbsoluteFill key={shot.id}>
          {renderShot(shot)}
        </AbsoluteFill>
      ))}

      {/* Audio — original clip */}
      <Audio src={staticFile(plan.audio_source)} />

      {/* Word captions — on top of everything */}
      {captions.length > 0 && (
        <WordCaptions captions={captions} />
      )}

      {/* Film grain */}
      <FilmGrain frame={frame} />
    </AbsoluteFill>
  );
};
