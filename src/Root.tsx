import React from "react";
import { Composition } from "remotion";
import { Minimal } from "./Minimal";
import { Cinematic } from "./Cinematic";
import { WebsitePromo } from "./WebsitePromo";
import { Combined } from "./Combined";
import { ProofVideo } from "./ProofVideo";
import { PersonalBrandIntro } from "./PersonalBrandIntro";
import { BodyOverWebsite } from "./BodyOverWebsite";
import { SmartEdit } from "./SmartEdit";
import { VisualPersonalityEngine } from "./VisualPersonalityEngine";

// 81 real templates from reactvideoeditor.com (MIT license)
import AnimatedList from "./fx/animated-list";
import AnimatedText from "./fx/animated-text";
import AreaChart from "./fx/area-chart";
import BlindsTransition from "./fx/blinds-transition";
import BokehCircles from "./fx/bokeh-circles";
import BounceText from "./fx/bounce-text";
import BubblePopText from "./fx/bubble-pop-text";
import CameraShake from "./fx/camera-shake";
import CardFlip from "./fx/card-flip";
import ChapterTitle from "./fx/chapter-title";
import ChartAnimation from "./fx/chart-animation";
import CinematicTitleIntro from "./fx/cinematic-title-intro";
import CircularProgress from "./fx/circular-progress";
import ClockWipe from "./fx/clock-wipe";
import ComparisonChart from "./fx/comparison-chart";
import CountdownIntro from "./fx/countdown-intro";
import CountdownTimer from "./fx/countdown-timer";
import CreditsRoll from "./fx/credits-roll";
import CrossDissolve from "./fx/cross-dissolve";
import DonutChart from "./fx/donut-chart";
import EndCard from "./fx/end-card";
import FadeThroughBlack from "./fx/fade-through-black";
import FilmBurn from "./fx/film-burn";
import FloatingBubbleText from "./fx/floating-bubble-text";
import GalleryGrid from "./fx/gallery-grid";
import GeometricPatterns from "./fx/geometric-patterns";
import GlitchText from "./fx/glitch-text";
import GradientShift from "./fx/gradient-shift";
import GridPulse from "./fx/grid-pulse";
import ImageCarousel from "./fx/image-carousel";
import ImageComparisonSlider from "./fx/image-comparison-slider";
import ImageZoomReveal from "./fx/image-zoom-reveal";
import IrisTransition from "./fx/iris-transition";
import KenBurns from "./fx/ken-burns";
import LetterboxReveal from "./fx/letterbox-reveal";
import LineChart from "./fx/line-chart";
import LiquidWave from "./fx/liquid-wave";
import LogoBlurReveal from "./fx/logo-blur-reveal";
import LogoBounceDrop from "./fx/logo-bounce-drop";
import LogoFadeReveal from "./fx/logo-fade-reveal";
import LogoGlitchReveal from "./fx/logo-glitch-reveal";
import LogoScaleRotate from "./fx/logo-scale-rotate";
import LogoSpinReveal from "./fx/logo-spin-reveal";
import LogoSplitReveal from "./fx/logo-split-reveal";
import LogoStrokeDraw from "./fx/logo-stroke-draw";
import LogoTypewriter from "./fx/logo-typewriter";
import LowerThird from "./fx/lower-third";
import MasonryGallery from "./fx/masonry-gallery";
import MatrixRain from "./fx/matrix-rain";
import MorphTransition from "./fx/morph-transition";
import NoiseGrain from "./fx/noise-grain";
import NotificationPop from "./fx/notification-pop";
import ParallaxPan from "./fx/parallax-pan";
import ParticleExplosion from "./fx/particle-explosion";
import PhotoStack from "./fx/photo-stack";
import PictureInPicture from "./fx/picture-in-picture";
import PieChart from "./fx/pie-chart";
import PixelTransition from "./fx/pixel-transition";
import PolaroidFrame from "./fx/polaroid-frame";
import PoppingText from "./fx/popping-text";
import ProgressBars from "./fx/progress-bars";
import ProgressSteps from "./fx/progress-steps";
import PulsingText from "./fx/pulsing-text";
import PushTransition from "./fx/push-transition";
import QuoteCard from "./fx/quote-card";
import RotatingCarousel from "./fx/rotating-carousel";
import SlideText from "./fx/slide-text";
import SlideWipe from "./fx/slide-wipe";
import SoundWave from "./fx/sound-wave";
import SplitScreen from "./fx/split-screen";
import SpotlightReveal from "./fx/spotlight-reveal";
import Starfield from "./fx/starfield";
import StatCounter from "./fx/stat-counter";
import SubscribeReminder from "./fx/subscribe-reminder";
import TextHighlight from "./fx/text-highlight";
import TitleSplit from "./fx/title-split";
import TypewriterSubtitle from "./fx/typewriter-subtitle";
import VignettePulse from "./fx/vignette-pulse";
import WhipPan from "./fx/whip-pan";
import ZoomPulse from "./fx/zoom-pulse";
import ZoomThrough from "./fx/zoom-through";

const FPS = 30;
const SHORT = 90;   // 3s — good for transitions/effects
const MEDIUM = 180; // 6s — good for intros/text
const LONG = 300;   // 10s — good for charts/carousels

export const Root: React.FC = () => (
  <>
    {/* === YOUR MAIN COMPOSITIONS === */}
    <Composition id="SmartEdit" component={SmartEdit} durationInFrames={888} fps={30} width={1080} height={1920} />
    <Composition id="ProofVideo" component={ProofVideo} durationInFrames={Math.ceil(16.18 * 30)} fps={30} width={1080} height={1920} />
    <Composition id="Minimal" component={Minimal} durationInFrames={Math.ceil(16.18 * 25)} fps={25} width={1080} height={1920} />
    <Composition id="Cinematic" component={Cinematic} durationInFrames={Math.ceil(16.18 * 25)} fps={25} width={1080} height={1920} />
    <Composition id="WebsitePromo" component={WebsitePromo} durationInFrames={Math.ceil(16.18 * 25)} fps={25} width={1080} height={1920} />
    <Composition id="Combined" component={Combined} durationInFrames={Math.ceil(16.18 * 25)} fps={25} width={1080} height={1920} />
    <Composition id="PersonalBrandIntro" component={PersonalBrandIntro} durationInFrames={Math.ceil(16.18 * 30)} fps={30} width={1080} height={1920} />
    <Composition id="BodyOverWebsite" component={BodyOverWebsite} durationInFrames={486} fps={30} width={1080} height={1920} />
    <Composition id="VisualPersonalityEngine" component={VisualPersonalityEngine} durationInFrames={888} fps={30} width={1080} height={1920} />

    {/* === 81 REAL TEMPLATES (reactvideoeditor.com, MIT) === */}

    {/* Text & Typography */}
    <Composition id="fx-AnimatedText"        component={AnimatedText}        durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-BounceText"          component={BounceText}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-BubblePopText"       component={BubblePopText}       durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-FloatingBubbleText"  component={FloatingBubbleText}  durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-GlitchText"          component={GlitchText}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PoppingText"         component={PoppingText}         durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PulsingText"         component={PulsingText}         durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SlideText"           component={SlideText}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-TextHighlight"       component={TextHighlight}       durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-TitleSplit"          component={TitleSplit}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-TypewriterSubtitle"  component={TypewriterSubtitle}  durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-QuoteCard"           component={QuoteCard}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ChapterTitle"        component={ChapterTitle}        durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LowerThird"          component={LowerThird}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Intros & Titles */}
    <Composition id="fx-CinematicTitleIntro" component={CinematicTitleIntro} durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CountdownIntro"      component={CountdownIntro}      durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CountdownTimer"      component={CountdownTimer}      durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LetterboxReveal"     component={LetterboxReveal}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SpotlightReveal"     component={SpotlightReveal}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Stats & Data */}
    <Composition id="fx-StatCounter"        component={StatCounter}         durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ProgressBars"       component={ProgressBars}        durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ProgressSteps"      component={ProgressSteps}       durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CircularProgress"   component={CircularProgress}    durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-AreaChart"          component={AreaChart}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LineChart"          component={LineChart}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PieChart"           component={PieChart}            durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-DonutChart"         component={DonutChart}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ChartAnimation"     component={ChartAnimation}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ComparisonChart"    component={ComparisonChart}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SoundWave"          component={SoundWave}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Transitions */}
    <Composition id="fx-BlindsTransition"   component={BlindsTransition}    durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ClockWipe"          component={ClockWipe}           durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CrossDissolve"      component={CrossDissolve}       durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-FadeThroughBlack"   component={FadeThroughBlack}    durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-FilmBurn"           component={FilmBurn}            durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-IrisTransition"     component={IrisTransition}      durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-MorphTransition"    component={MorphTransition}     durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PixelTransition"    component={PixelTransition}     durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PushTransition"     component={PushTransition}      durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SlideWipe"          component={SlideWipe}           durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-WhipPan"            component={WhipPan}             durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ZoomThrough"        component={ZoomThrough}         durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />

    {/* Backgrounds & Effects */}
    <Composition id="fx-BokehCircles"       component={BokehCircles}        durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CameraShake"        component={CameraShake}         durationInFrames={SHORT}  fps={FPS} width={1080} height={1920} />
    <Composition id="fx-GeometricPatterns"  component={GeometricPatterns}   durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-GradientShift"      component={GradientShift}       durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-GridPulse"          component={GridPulse}           durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LiquidWave"         component={LiquidWave}          durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-MatrixRain"         component={MatrixRain}          durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-NoiseGrain"         component={NoiseGrain}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ParticleExplosion"  component={ParticleExplosion}   durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-Starfield"          component={Starfield}           durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-VignettePulse"      component={VignettePulse}       durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ZoomPulse"          component={ZoomPulse}           durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Logo & Branding */}
    <Composition id="fx-LogoBlurReveal"     component={LogoBlurReveal}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoBounceDrop"     component={LogoBounceDrop}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoFadeReveal"     component={LogoFadeReveal}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoGlitchReveal"   component={LogoGlitchReveal}    durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoScaleRotate"    component={LogoScaleRotate}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoSpinReveal"     component={LogoSpinReveal}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoSplitReveal"    component={LogoSplitReveal}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoStrokeDraw"     component={LogoStrokeDraw}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-LogoTypewriter"     component={LogoTypewriter}      durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Galleries & Media */}
    <Composition id="fx-AnimatedList"       component={AnimatedList}        durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CardFlip"           component={CardFlip}            durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-GalleryGrid"        component={GalleryGrid}         durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ImageCarousel"      component={ImageCarousel}       durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ImageComparisonSlider" component={ImageComparisonSlider} durationInFrames={LONG} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ImageZoomReveal"    component={ImageZoomReveal}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-KenBurns"           component={KenBurns}            durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-MasonryGallery"     component={MasonryGallery}      durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-ParallaxPan"        component={ParallaxPan}         durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PhotoStack"         component={PhotoStack}          durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PictureInPicture"   component={PictureInPicture}    durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-PolaroidFrame"      component={PolaroidFrame}       durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-RotatingCarousel"   component={RotatingCarousel}    durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SplitScreen"        component={SplitScreen}         durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />

    {/* Social & End Cards */}
    <Composition id="fx-EndCard"            component={EndCard}             durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-NotificationPop"    component={NotificationPop}     durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-SubscribeReminder"  component={SubscribeReminder}   durationInFrames={MEDIUM} fps={FPS} width={1080} height={1920} />
    <Composition id="fx-CreditsRoll"        component={CreditsRoll}         durationInFrames={LONG}   fps={FPS} width={1080} height={1920} />
  </>
);
