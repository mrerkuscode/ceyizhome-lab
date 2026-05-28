export type CapitalConnectionFix = {
  nextLowercaseOffset: number;
  baselineAdjust: number;
};

export const capitalConnectionFixMap: Record<string, CapitalConnectionFix> = {
  A: { nextLowercaseOffset: -8, baselineAdjust: 0 },
  B: { nextLowercaseOffset: -5, baselineAdjust: 0 },
  C: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  Ç: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  D: { nextLowercaseOffset: -5, baselineAdjust: 0 },
  E: { nextLowercaseOffset: -5, baselineAdjust: 0 },
  G: { nextLowercaseOffset: -6, baselineAdjust: 0 },
  İ: { nextLowercaseOffset: -4, baselineAdjust: 0 },
  M: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  N: { nextLowercaseOffset: -5, baselineAdjust: 0 },
  O: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  Ö: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  S: { nextLowercaseOffset: -6, baselineAdjust: 0 },
  Ş: { nextLowercaseOffset: -6, baselineAdjust: 0 },
  T: { nextLowercaseOffset: -7, baselineAdjust: 0 },
  Z: { nextLowercaseOffset: -5, baselineAdjust: 0 },
};
