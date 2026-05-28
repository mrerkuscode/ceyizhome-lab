export type PunctuationFix = {
  spacingBefore: number;
  spacingAfter: number;
  baselineAdjust: number;
  fallback: "font" | "svg";
  note?: string;
};

export const punctuationFixMap: Record<string, PunctuationFix> = {
  ".": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 2, fallback: "font" },
  ",": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 3, fallback: "font" },
  ":": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 1, fallback: "font" },
  ";": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 2, fallback: "font" },
  "!": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "font" },
  "?": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "font" },
  "-": { spacingBefore: 2, spacingAfter: 2, baselineAdjust: -2, fallback: "font" },
  "_": { spacingBefore: 2, spacingAfter: 2, baselineAdjust: 6, fallback: "font" },
  "/": { spacingBefore: 1, spacingAfter: 2, baselineAdjust: 0, fallback: "font" },
  "&": { spacingBefore: 3, spacingAfter: 3, baselineAdjust: 0, fallback: "font" },
  "+": { spacingBefore: 3, spacingAfter: 3, baselineAdjust: 0, fallback: "font" },
  "@": { spacingBefore: 2, spacingAfter: 3, baselineAdjust: 0, fallback: "font" },
  "₺": {
    spacingBefore: 1,
    spacingAfter: 2,
    baselineAdjust: 0,
    fallback: "svg",
    note: "Mochary.ttf coverage analizinde TRY glyph yoksa SVG fallback kullanilir.",
  },
  "'": { spacingBefore: -2, spacingAfter: 0, baselineAdjust: -5, fallback: "font" },
  '"': { spacingBefore: -1, spacingAfter: 1, baselineAdjust: -5, fallback: "font" },
  "(": { spacingBefore: 2, spacingAfter: 0, baselineAdjust: 0, fallback: "font" },
  ")": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "font" },
};
