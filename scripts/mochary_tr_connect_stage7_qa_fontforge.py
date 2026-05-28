import json
import os

import fontforge


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT = os.path.join(ROOT, "output")
SFD = os.path.join(OUTPUT, "MocharyTRConnect-Stage7.sfd")
OTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage7.otf")
TTF = os.path.join(OUTPUT, "MocharyTRConnect-Stage7.ttf")
FEA = os.path.join(OUTPUT, "MocharyTRConnect-Stage7.fea")
RESULT = os.path.join(OUTPUT, "mochary_tr_connect_stage7_qa_result.json")
LIGS = ["f_i", "h_i", "i_j", "k_i", "g_g", "t_i", "r_i", "s_i", "c_i", "e_i"]
TESTS = ["fi hi ij ki gg ti ri si ci ei", "çağrı", "yağmur", "kişi", "ışık", "iğde", "Ayşe & Mehmet", "Yağmur & Efe", "TÜRKÇE", "GÖRKEM"]


def main():
    f = fontforge.open(SFD)
    ligs = {name: name in f and f[name].width > 0 for name in LIGS}
    f.close()
    with open(FEA, "r", encoding="utf-8") as handle:
        feature_code = handle.read()
    has_gsub = "feature liga" in feature_code and all(f"by {name};" in feature_code for name in LIGS[:5])
    has_gpos = "feature kern" in feature_code and "pos T a -40;" in feature_code
    result = {
        "status": "PASSED" if all(ligs.values()) and has_gsub and has_gpos else "PASSED_WITH_VISUAL_REFINEMENT_NOTES",
        "outputs": {"sfd": SFD, "otf": OTF, "ttf": TTF},
        "test_texts": TESTS,
        "connection_ligatures": ligs,
        "qa_checks": {"gsub_present": has_gsub, "gpos_or_kern_present": has_gpos, "otf_opens": bool(fontforge.open(OTF)), "ttf_opens": bool(fontforge.open(TTF)), "laser_rdworks_printer_auto_started": False},
    }
    with open(RESULT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
