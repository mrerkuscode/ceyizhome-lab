export type CapitalConnectionFix =
  | {
      mode: "manualBridge";
      nextLowercaseOffset: number;
      baselineAdjust: number;
      bridgeWidth?: number;
    }
  | {
      mode: "fontVariant";
      variant: string;
      nextLowercaseOffset?: number;
      baselineAdjust?: number;
    };

export const capitalConnectionFixMap: Record<string, CapitalConnectionFix> = {
  S: { mode: "manualBridge", nextLowercaseOffset: -6, baselineAdjust: 0, bridgeWidth: 1.2 },
  L: { mode: "manualBridge", nextLowercaseOffset: -7, baselineAdjust: 0, bridgeWidth: 1.2 },
  M: { mode: "manualBridge", nextLowercaseOffset: -8, baselineAdjust: 0, bridgeWidth: 1.4 },
  C: { mode: "manualBridge", nextLowercaseOffset: -6, baselineAdjust: 0, bridgeWidth: 1.1 },
  Z: { mode: "manualBridge", nextLowercaseOffset: -6, baselineAdjust: 0, bridgeWidth: 1.1 },
  A: { mode: "fontVariant", variant: "A_con", nextLowercaseOffset: -4, baselineAdjust: 0 },
  F: { mode: "fontVariant", variant: "F_con", nextLowercaseOffset: -4, baselineAdjust: 0 },
  H: { mode: "fontVariant", variant: "H_con", nextLowercaseOffset: -4, baselineAdjust: 0 },
  X: { mode: "fontVariant", variant: "X_con", nextLowercaseOffset: -4, baselineAdjust: 0 },
};

export const connectedCapitalVariantNames = ["A_con", "F_con", "H_con", "X_con"] as const;
export const missingConnectedCapitalVariantNames = ["S_con", "L_con", "M_con"] as const;
