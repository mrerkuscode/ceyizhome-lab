"""Etiket Studio inspector tabs functional test."""
from pathlib import Path


def test_inspector_panels_exist_in_html():
    html = Path("src/webui/index.html").read_text(encoding="utf-8")
    for panel in ["fields", "style", "layout", "output"]:
        assert f'data-panel="{panel}"' in html, f"Panel {panel} not found"


def test_inspector_tabs_have_handler_in_js():
    js = Path("src/webui/app.js").read_text(encoding="utf-8")
    assert "initStudioInspectorTabs" in js, "Tab init function missing"
    assert "data-tab" in js, "Tab data attr handling missing"
