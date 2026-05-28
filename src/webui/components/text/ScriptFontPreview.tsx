import type { CSSProperties } from "react";
import { capitalConnectionFixMap } from "../../lib/fonts/capitalConnectionFixMap";
import { punctuationFixMap } from "../../lib/fonts/punctuationFixMap";

export type ScriptFontFeatureOptions = {
  ligatures?: boolean;
  contextualAlternates?: boolean;
  stylisticAlternates?: boolean;
  kerning?: boolean;
  connectionFix?: boolean;
  punctuationFix?: boolean;
  letterSpacing?: number;
  wordSpacing?: number;
  baseline?: number;
};

export type ScriptFontPreviewProps = {
  text: string;
  fontFamily?: string;
  options?: ScriptFontFeatureOptions;
};

const TURKISH_LOWERCASE = /^[a-zçğıöşü]$/u;

export function scriptFontFeatureSettings(options: ScriptFontFeatureOptions = {}): string {
  const ligatures = options.ligatures !== false;
  const contextualAlternates = options.contextualAlternates !== false;
  const stylisticAlternates = options.stylisticAlternates !== false;
  const kerning = options.kerning !== false;
  return `"liga" ${ligatures ? 1 : 0}, "clig" ${ligatures ? 1 : 0}, "calt" ${contextualAlternates ? 1 : 0}, "kern" ${kerning ? 1 : 0}, "salt" ${stylisticAlternates ? 1 : 0}`;
}

export function scriptFontPreviewStyle(fontFamily = "Mochary Personal Use Only", options: ScriptFontFeatureOptions = {}): CSSProperties {
  return {
    fontFamily: `"${fontFamily}", "Great Vibes", "Segoe Script", cursive`,
    fontKerning: options.kerning === false ? "none" : "normal",
    textRendering: "optimizeLegibility",
    fontFeatureSettings: scriptFontFeatureSettings(options),
    letterSpacing: `${options.letterSpacing ?? 0}px`,
    wordSpacing: `${options.wordSpacing ?? 0}px`,
    transform: `translateY(${options.baseline ?? 0}px)`,
  };
}

function charFixStyle(chars: string[], index: number, options: ScriptFontFeatureOptions): CSSProperties {
  const char = chars[index] || "";
  const prev = chars[index - 1] || "";
  let marginLeft = 0;
  let top = 0;
  if (options.connectionFix !== false && TURKISH_LOWERCASE.test(char)) {
    const fix = capitalConnectionFixMap[prev];
    if (fix) {
      marginLeft += fix.nextLowercaseOffset ?? 0;
      top += fix.baselineAdjust ?? 0;
    }
  }
  if (options.punctuationFix !== false) {
    const fix = punctuationFixMap[char];
    if (fix) {
      marginLeft += fix.spacingBefore;
      top += fix.baselineAdjust;
    }
  }
  return { display: "inline-block", position: "relative", marginLeft, top };
}

export function ScriptFontPreview({ text, fontFamily = "Mochary Personal Use Only", options = {} }: ScriptFontPreviewProps) {
  const chars = [...(text || "")];
  return (
    <div className="script-font-preview" style={scriptFontPreviewStyle(fontFamily, options)}>
      {options.connectionFix === false && options.punctuationFix === false
        ? text
        : chars.map((char, index) => (
            <span key={`${char}-${index}`} style={charFixStyle(chars, index, options)}>
              {char}
            </span>
          ))}
    </div>
  );
}
