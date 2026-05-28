export type PunctuationFix = {
  spacingBefore: number;
  spacingAfter: number;
  baselineAdjust: number;
  fallback: string;
};

export const punctuationFixMap: Record<string, PunctuationFix> = {
  ".": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 2, fallback: "dot" },
  ",": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 3, fallback: "comma" },
  ":": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 1, fallback: "colon" },
  ";": { spacingBefore: -1, spacingAfter: 2, baselineAdjust: 2, fallback: "semicolon" },
  "!": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "exclamation" },
  "?": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "question" },
  "-": { spacingBefore: 2, spacingAfter: 2, baselineAdjust: -2, fallback: "dash" },
  "_": { spacingBefore: 2, spacingAfter: 2, baselineAdjust: 6, fallback: "underscore" },
  "/": { spacingBefore: 1, spacingAfter: 2, baselineAdjust: 0, fallback: "slash" },
  "&": { spacingBefore: 3, spacingAfter: 3, baselineAdjust: 0, fallback: "ampersand" },
  "+": { spacingBefore: 3, spacingAfter: 3, baselineAdjust: 0, fallback: "plus" },
  "@": { spacingBefore: 2, spacingAfter: 3, baselineAdjust: 0, fallback: "at" },
  "₺": { spacingBefore: 1, spacingAfter: 2, baselineAdjust: 0, fallback: "try" },
  "'": { spacingBefore: -2, spacingAfter: 0, baselineAdjust: -5, fallback: "apostrophe" },
  "\"": { spacingBefore: -1, spacingAfter: 1, baselineAdjust: -5, fallback: "quote" },
  "(": { spacingBefore: 2, spacingAfter: 0, baselineAdjust: 0, fallback: "paren-left" },
  ")": { spacingBefore: 0, spacingAfter: 2, baselineAdjust: 0, fallback: "paren-right" },
};
