export const fontProfiles = {
  ceyizhomeLabScript: {
    displayName: "Ceyizhome Lab Script",
    baseFontFamily: "Mochary",
    opentypeFeatures: {
      liga: true,
      clig: true,
      calt: true,
      kern: true,
      salt: true,
    },
    defaultLetterSpacing: 0,
    defaultWordSpacing: 8,
    defaultBaseline: 0,
    weldInsideName: true,
    keepNamesSeparate: true,
    exportAsPath: true,
    capitalConnectionFix: true,
    punctuationFix: true,
    tryFallback: "svg",
  },
} as const;

export type FontProfileId = keyof typeof fontProfiles;
