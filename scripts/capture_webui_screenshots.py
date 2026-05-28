from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from desktop.web_main_window import WebMainWindow  # noqa: E402
from webui_backend import bulk_label_api, template_api  # noqa: E402


SCREENS = [
    ("home", "ana_sayfa.png"),
    ("labelModels", "etiket_modelleri.png"),
    ("bulkLabel", "toplu_etiket.png"),
    ("bulkGallery", "toplu_etiket_galeri.png"),
    ("label", "manuel_etiket.png"),
    ("labelOutputs", "etiket_ciktilari.png"),
    ("printQueue", "yazdirma_sirasi.png"),
    ("trendyolOrders", "trendyol_siparisler.png"),
    ("reports", "raporlar.png"),
    ("settings", "ayarlar.png"),
]


def bulk_gallery_seed() -> str:
    sample_excel = PROJECT_ROOT / "examples" / "toplu_etiket_ornek.xlsx"
    if not sample_excel.exists():
        return "[]"
    models = template_api.list_label_model_gallery(PROJECT_ROOT)
    items = bulk_label_api.bulk_gallery_items(PROJECT_ROOT, sample_excel, models)
    return json.dumps(items, ensure_ascii=False)


BULK_GALLERY_SEED = bulk_gallery_seed()


def inject_bulk_gallery_script(open_modal: bool = False) -> str:
    modal_part = "openBulkGalleryEditor(0);" if open_modal else ""
    return f"""
    showSection('bulkLabel');
    currentState.readiness = 'HAZIR';
    currentState.summary = currentState.summary || {{}};
    bulkGalleryItems = {BULK_GALLERY_SEED};
    if (bulkGalleryItems.length) {{
      selectedBulkGalleryItemId = bulkGalleryItems[0].item_id || '';
      renderBulkGallery();
      {modal_part}
    }}
    setTimeout(() => {{
      const target = document.getElementById('bulkGalleryGrid');
      if (target) target.scrollIntoView({{ block: 'center' }});
    }}, 250);
    """

MODAL_SCREENS = [
    (
        "yeni_model_ekle_modal.png",
        "showSection('labelModels'); openNewLabelModelWizard();",
    ),
    (
        "etiket_modelleri_onizle_modal.png",
        """
        closeNewLabelModelWizard();
        showSection('labelModels');
        if (!selectedLabelModel && currentLabelModels.length) selectLabelModel(currentLabelModels[0].path);
        previewSelectedModelOnly();
        """,
    ),
    (
        "etiket_modelleri_filtre_hazir.png",
        """
        closeModelPreviewModal();
        closeNewLabelModelWizard();
        showSection('labelModels');
        setModelHealthFilter('Hazır');
        """,
    ),
    (
        "etiket_modelleri_gorsel_eksik.png",
        """
        showSection('labelModels');
        setModelHealthFilter('Görsel eksik');
        """,
    ),
    (
        "etiket_modelleri_model_kontrol.png",
        """
        showSection('labelModels');
        clearModelFilters();
        if (!selectedLabelModel && currentLabelModels.length) selectLabelModel(currentLabelModels[0].path);
        runSelectedModelHealthCheck();
        """,
    ),
    (
        "etiket_modelleri_varyant_modal.png",
        """
        showSection('labelModels');
        closeModelPreviewModal();
        if (!selectedLabelModel && currentLabelModels.length) selectLabelModel(currentLabelModels[0].path);
        openCloneLabelModelWizard();
        """,
    ),
    (
        "etiket_modelleri_teknik_mod_acik.png",
        """
        closeCloneLabelModelWizard();
        showSection('labelModels');
        clearModelFilters();
        if (!document.getElementById('labelTechnicalMode').checked) document.getElementById('labelTechnicalMode').click();
        """,
    ),
    (
        "toplu_etiket_galeri_duzenle_modal.png",
        """
        closeModelPreviewModal();
        closeNewLabelModelWizard();
        """
        + inject_bulk_gallery_script(open_modal=True),
    ),
    (
        "release_dashboard.png",
        "closeModelPreviewModal(); closeNewLabelModelWizard(); showSection('reports'); selectReport('release');",
    ),
    (
        "etiket_ciktilari_teknik_arsiv.png",
        "showSection('labelOutputs'); selectLabelOutputTab('technical');",
    ),
    (
        "etiket_ciktilari_filtre_pdf.png",
        "showSection('labelOutputs'); selectLabelOutputTab('pdf');",
    ),
    (
        "etiket_ciktilari_yazdir_modal.png",
        """
        showSection('labelOutputs');
        selectLabelOutputTab('all');
        setTimeout(() => {
          const printButton = [...document.querySelectorAll('#labelOutputList button')]
            .find(button => (button.textContent || '').includes('Yazdır'));
          if (printButton) printButton.click();
        }, 450);
        """,
    ),
    (
        "yazdirma_sirasi_yazdir_modal.png",
        """
        if (typeof closeSafePrintModal === 'function') closeSafePrintModal();
        showSection('printQueue');
        updatePrintQueue(currentState.printQueue || []);
        setTimeout(() => {
          const printButton = [...document.querySelectorAll('#printQueueList button')]
            .find(button => (button.textContent || '').includes('Yazdır'));
          if (printButton) printButton.click();
        }, 450);
        """,
    ),
    (
        "yazdirma_sirasi_filtre_bekleyen.png",
        """
        if (typeof closeSafePrintModal === 'function') closeSafePrintModal();
        showSection('printQueue');
        if (document.getElementById('queueStatusFilter')) document.getElementById('queueStatusFilter').value = 'pending';
        refreshPrintQueueFilters();
        """,
    ),
    (
        "yazdirma_sirasi_toplu_secim.png",
        """
        showSection('printQueue');
        updatePrintQueue(currentState.printQueue || []);
        setTimeout(() => {
          const first = document.querySelector('#printQueueList input[type="checkbox"]');
          if (first && !first.checked) first.click();
        }, 350);
        """,
    ),
    (
        "yazdirma_sirasi_temizle_modal.png",
        """
        showSection('printQueue');
        updatePrintQueue(currentState.printQueue || []);
        setTimeout(() => { if (typeof confirmClearPrintQueue === 'function') confirmClearPrintQueue(); }, 350);
        """,
    ),
]


def main() -> int:
    app = QApplication(sys.argv)
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    window = WebMainWindow(PROJECT_ROOT, python_exe)
    window.resize(1500, 900)
    window.show()
    output_dir = PROJECT_ROOT / "output" / date.today().isoformat() / "ui_screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    index = {"value": 0}

    def capture_current() -> None:
        screen_id, filename = SCREENS[index["value"]]
        if screen_id in {"bulkLabel", "bulkGallery"}:
            sample_excel = PROJECT_ROOT / "examples" / "toplu_etiket_ornek.xlsx"
            if sample_excel.exists():
                window.set_selected_excel(sample_excel)
        if screen_id == "label":
            window.view.page().runJavaScript(
                """
                showSection('label');
                if (window.currentLabelModels && currentLabelModels.length && !selectedLabelModel) {
                    selectLabelModel(currentLabelModels[0].path);
                }
                if (document.getElementById('manualText')) document.getElementById('manualText').value = 'Ayşe & Mehmet QA';
                if (document.getElementById('manualDateText')) document.getElementById('manualDateText').value = '15.05.26';
                if (document.getElementById('manualNoteText')) document.getElementById('manualNoteText').value = 'Nişan hatırası';
                updateManualFieldValue('label_text', 'Ayşe & Mehmet QA');
                updateManualFieldValue('date_text', '15.05.26');
                updateManualFieldValue('note_text', 'Nişan hatırası');
                showManualPreviewPlaceholder();
                scheduleFieldOverlaySync();
                """
            )
        elif screen_id == "bulkGallery":
            window.view.page().runJavaScript(inject_bulk_gallery_script(open_modal=False))
        elif screen_id == "labelOutputs":
            window.view.page().runJavaScript(
                """
                if (typeof closeSafePrintModal === 'function') closeSafePrintModal();
                if (typeof closeModelPreviewModal === 'function') closeModelPreviewModal();
                if (typeof closeNewLabelModelWizard === 'function') closeNewLabelModelWizard();
                showSection('labelOutputs');
                updateLabelOutputs(currentState.labelOutputs || []);
                setTimeout(() => {
                  const first = document.querySelector('#labelOutputList .output-card:not(.technical-output-item)');
                  if (first) first.click();
                }, 350);
                """
            )
        elif screen_id == "printQueue":
            window.view.page().runJavaScript(
                """
                if (typeof closeSafePrintModal === 'function') closeSafePrintModal();
                if (typeof closeQueueClearModal === 'function') closeQueueClearModal();
                showSection('printQueue');
                updatePrintQueue(currentState.printQueue || []);
                setTimeout(() => {
                  const first = document.querySelector('#printQueueList .queue-job-card');
                  if (first) first.click();
                }, 350);
                """
            )
        else:
            window.view.page().runJavaScript(f"showSection('{screen_id}');")
        visual_delay = {
            "labelModels": 2600,
            "label": 4600,
            "labelOutputs": 2600,
            "printQueue": 1400,
        }.get(screen_id, 1000)
        QTimer.singleShot(visual_delay, lambda: save_current(filename, screen_id))

    def save_current(filename: str, screen_id: str, attempts: int = 0) -> None:
        if screen_id == "labelModels" and attempts < 10:
            window.view.page().runJavaScript(
                """
                (() => {
                  const images = [...document.querySelectorAll('#labelModels .model-preview img, #labelModels .large-preview img')]
                    .filter(img => img.offsetParent !== null);
                  return {
                    count: images.length,
                    loaded: images.filter(img => img.complete && img.naturalWidth > 0).length
                  };
                })()
                """,
                lambda state: (
                    QTimer.singleShot(600, lambda: save_current(filename, screen_id, attempts + 1))
                    if (state or {}).get("count", 0) > 0 and (state or {}).get("loaded", 0) == 0
                    else QTimer.singleShot(900, lambda: save_current_now(filename))
                ),
            )
            return
        if screen_id == "labelOutputs" and attempts < 6:
            window.view.page().runJavaScript(
                """
                (() => {
                  const active = document.querySelector('.page.active')?.id || '';
                  if (active !== 'labelOutputs') {
                    showSection('labelOutputs');
                    updateLabelOutputs(currentState.labelOutputs || []);
                  }
                  return {
                    active,
                    cards: document.querySelectorAll('#labelOutputList .output-card').length
                  };
                })()
                """,
                lambda state: (
                    QTimer.singleShot(700, lambda: save_current(filename, screen_id, attempts + 1))
                    if (state or {}).get("active") != "labelOutputs"
                    else QTimer.singleShot(900, lambda: save_current_now(filename))
                ),
            )
            return
        save_current_now(filename)

    def save_current_now(filename: str) -> None:
        pixmap = window.view.grab()
        pixmap.save(str(output_dir / filename))
        index["value"] += 1
        if index["value"] >= len(SCREENS):
            modal_index["value"] = 0
            QTimer.singleShot(450, capture_modal)
            return
        QTimer.singleShot(450, capture_current)

    modal_index = {"value": 0}

    def capture_modal() -> None:
        if modal_index["value"] >= len(MODAL_SCREENS):
            window.close()
            app.quit()
            return
        filename, script = MODAL_SCREENS[modal_index["value"]]
        window.view.page().runJavaScript(script)
        QTimer.singleShot(1100, lambda: save_modal(filename))

    def save_modal(filename: str) -> None:
        pixmap = window.view.grab()
        pixmap.save(str(output_dir / filename))
        modal_index["value"] += 1
        QTimer.singleShot(450, capture_modal)

    window.view.loadFinished.connect(lambda _ok: QTimer.singleShot(1800, capture_current))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
