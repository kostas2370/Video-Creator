export const videoFormats = [
  { value: "LANDSCAPE", label: "Landscape", ratio: "16:9", shape: "w-12 aspect-video", size: [1920, 1080] },
  { value: "PORTRAIT", label: "Portrait", ratio: "9:16", shape: "h-10 aspect-[9/16]", size: [1080, 1920] },
  { value: "SQUARE", label: "Square", ratio: "1:1", shape: "h-9 aspect-square", size: [1080, 1080] },
];

export const videoFrameSize = format => videoFormats.find(item => item.value === format)?.size ?? videoFormats[0].size;
