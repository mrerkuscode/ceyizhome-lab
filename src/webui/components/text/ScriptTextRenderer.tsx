import type { CSSProperties } from "react";
import { capitalConnectionFixMap } from "../../lib/fonts/capitalConnectionFixMap";
import { punctuationFixMap } from "../../lib/fonts/punctuationFixMap";
import { fontProfiles } from "../../lib/fonts/fontProfiles";

export type ScriptTextRendererOptions = {
  fontFamily?: string;
  fontSize?: number;
  ligatures?: boolean;
  contextualAlternates?: boolean;
  stylisticAlternates?: boolean;
  kerning?: boolean;
  capitalConnectionFix?: boolean;
  punctuationFix?: boolean;
  weldInsideName?: boolean;
  exportAsPath?: boolean;
  letterSpacing?: number;
  wordSpacing?: number;
  baseline?: number;
  scaleX?: number;
  scaleY?: number;
};

export type ScriptTextObject = {
  id: string;
  text: string;
  bounds: { x: number; y: number; width: number; height: number; baseline: number };
  exportMode: "path" | "text";
  weldInsideName: boolean;
  keepSeparateObject: boolean;
};

export type ScriptTextRendererProps = {
  text: string;
  id?: string;
  selected?: boolean;
  options?: ScriptTextRendererOptions;
  onMeasure?: (object: ScriptTextObject) => void;
};

const TURKISH_LOWERCASE = /^[a-zçğıöşü]$/u;

export function scriptTextFeatureSettings(options: ScriptTextRendererOptions = {}): string {
  const defaults = fontProfiles.ceyizhomeLabScript.opentypeFeatures;
  const ligatures = options.ligatures ?? defaults.liga;
  const contextualAlternates = options.contextualAlternates ?? defaults.calt;
  const stylisticAlternates = options.stylisticAlternates ?? defaults.salt;
  const kerning = options.kerning ?? defaults.kern;
  return `"liga" ${ligatures ? 1 : 0}, "clig" ${ligatures ? 1 : 0}, "calt" ${contextualAlternates ? 1 : 0}, "kern" ${kerning ? 1 : 0}, "salt" ${stylisticAlternates ? 1 : 0}`;
}

export function scriptTextStyle(options: ScriptTextRendererOptions = {}): CSSProperties {
  const profile = fontProfiles.ceyizhomeLabScript;
  const fontFamily = options.fontFamily || profile.displayName;
  return {
    fontFamily: `"${fontFamily}", "Mochary Personal Use Only", "Mochary Use Personal", "Great Vibes", "Segoe Script", cursive`,
    fontSize: options.fontSize ? `${options.fontSize}px` : undefined,
    fontKerning: options.kerning === false ? "none" : "normal",
    textRendering: "optimizeLegibility",
    fontFeatureSettings: scriptTextFeatureSettings(options),
    letterSpacing: `${options.letterSpacing ?? profile.defaultLetterSpacing}px`,
    wordSpacing: `${options.wordSpacing ?? profile.defaultWordSpacing}px`,
    transform: `translateY(${options.baseline ?? profile.defaultBaseline}px) scale(${options.scaleX ?? 1}, ${options.scaleY ?? 1})`,
    transformOrigin: "left center",
  };
}

function characterStyle(chars: string[], index: number, options: ScriptTextRendererOptions): CSSProperties {
  const char = chars[index] || "";
  const prev = chars[index - 1] || "";
  let marginLeft = 0;
  let top = 0;
  const capFix = options.capitalConnectionFix !== false && TURKISH_LOWERCASE.test(char) ? capitalConnectionFixMap[prev] : null;
  if (capFix) {
    marginLeft += capFix.nextLowercaseOffset ?? 0;
    top += capFix.baselineAdjust ?? 0;
  }
  const punctFix = options.punctuationFix !== false ? punctuationFixMap[char] : null;
  if (punctFix) {
    marginLeft += punctFix.spacingBefore;
    top += punctFix.baselineAdjust;
  }
  return { display: "inline-block", position: "relative", marginLeft, top };
}

export function estimateScriptTextObject(text: string, id = "script-text", options: ScriptTextRendererOptions = {}): ScriptTextObject {
  const fontSize = options.fontSize ?? 72;
  const compactLength = Math.max(1, [...String(text || "").replace(/\s+/g, "")].length);
  const wordCount = Math.max(1, String(text || "").trim().split(/\s+/).filter(Boolean).length);
  const width = (compactLength * fontSize * 0.48) + ((wordCount - 1) * (options.wordSpacing ?? fontProfiles.ceyizhomeLabScript.defaultWordSpacing));
  const height = fontSize * 1.1;
  return {
    id,
    text,
    bounds: { x: 0, y: 0, width: Number(width.toFixed(2)), height: Number(height.toFixed(2)), baseline: Number((fontSize * 0.78).toFixed(2)) },
    exportMode: options.exportAsPath === false ? "text" : "path",
    weldInsideName: options.weldInsideName !== false,
    keepSeparateObject: true,
  };
}

export function ScriptTextRenderer({ text, id = "script-text", selected = false, options = {}, onMeasure }: ScriptTextRendererProps) {
  const chars = [...(text || "")];
  const object = estimateScriptTextObject(text, id, options);
  onMeasure?.(object);
  return (
    <span
      className={`script-text-renderer${selected ? " selected" : ""}`}
      data-script-object-id={object.id}
      data-export-mode={object.exportMode}
      data-weld-inside-name={object.weldInsideName ? "true" : "false"}
      data-keep-names-separate="true"
      style={scriptTextStyle(options)}
      title={`${object.bounds.width} x ${object.bounds.height}px · ${object.exportMode}`}
    >
      {options.capitalConnectionFix === false && options.punctuationFix === false
        ? text
        : chars.map((char, index) => (
            <span key={`${char}-${index}`} style={characterStyle(chars, index, options)}>
              {char === "₺" && punctuationFixMap["₺"].fallback === "svg" ? "₺" : char}
            </span>
          ))}
      {selected ? <i className="script-text-bounds" aria-hidden="true" /> : null}
    </span>
  );
}
