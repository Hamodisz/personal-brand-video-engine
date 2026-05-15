import { Config } from "@remotion/cli/config";
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setPixelFormat("yuv420p");
Config.setDelayRenderTimeoutInMilliseconds(90000);
Config.overrideFfmpegCommand(({ args }) => {
  // Force yuv420p — Remotion defaults to yuvj420p which QuickTime can't hardware-decode
  const idx = args.indexOf("-pix_fmt");
  if (idx !== -1) {
    const out = [...args];
    out[idx + 1] = "yuv420p";
    return out;
  }
  return [...args, "-pix_fmt", "yuv420p"];
});
