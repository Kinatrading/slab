from __future__ import annotations

import logging
import sys
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import AppConfig, load_config, save_config
from models import PairResult
from slab_scanner import analyze_pairs, fetch_all_slabs
from steam_client import SteamClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.config = config
        self.saved_config: AppConfig | None = None
        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.cookie_edit = QTextEdit()
        form.addRow("Cookie String", self.cookie_edit)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        form.addRow("Request Delay (ms)", self.delay_spin)

        self.proxy_edit = QTextEdit()
        form.addRow("Proxy List", self.proxy_edit)

        self.country_edit = QLineEdit()
        form.addRow("Country", self.country_edit)

        self.language_edit = QLineEdit()
        form.addRow("Language", self.language_edit)

        self.currency_spin = QSpinBox()
        self.currency_spin.setRange(0, 999)
        form.addRow("Currency ID", self.currency_spin)

        self.diff_more_spin = QDoubleSpinBox()
        self.diff_more_spin.setRange(0, 1000)
        self.diff_more_spin.setDecimals(2)
        form.addRow("Diff when slab more expensive", self.diff_more_spin)

        self.diff_less_spin = QDoubleSpinBox()
        self.diff_less_spin.setRange(0, 1000)
        self.diff_less_spin.setDecimals(2)
        form.addRow("Diff when slab cheaper", self.diff_less_spin)

        layout.addLayout(form)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self._save)
        layout.addWidget(save_button)

    def _populate_fields(self) -> None:
        self.cookie_edit.setPlainText(self.config.cookie_string)
        self.delay_spin.setValue(self.config.request_delay_ms)
        self.proxy_edit.setPlainText("\n".join(self.config.normalized_proxies()))
        self.country_edit.setText(self.config.country)
        self.language_edit.setText(self.config.language)
        self.currency_spin.setValue(self.config.currency_id)
        self.diff_more_spin.setValue(self.config.diff_when_slab_more_expensive)
        self.diff_less_spin.setValue(self.config.diff_when_slab_cheaper)

    def _save(self) -> None:
        new_config = AppConfig(
            cookie_string=self.cookie_edit.toPlainText().strip(),
            request_delay_ms=self.delay_spin.value(),
            proxy_list=[p.strip() for p in self.proxy_edit.toPlainText().splitlines()],
            country=self.country_edit.text().strip() or "US",
            language=self.language_edit.text().strip() or "english",
            currency_id=self.currency_spin.value(),
            diff_when_slab_more_expensive=self.diff_more_spin.value(),
            diff_when_slab_cheaper=self.diff_less_spin.value(),
        )
        save_config(new_config)
        self.saved_config = new_config
        QMessageBox.information(self, "Saved", "Settings saved successfully.")
        self.accept()


class ScanWorker(QThread):
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:  # noqa: D401
        try:
            client = SteamClient(self.config)
            slabs = fetch_all_slabs(client)
            if not slabs:
                logging.error("No slab data fetched from Steam search API.")
                self.error.emit("No slab data fetched.")
                return

            def progress_cb(done: int, total: int) -> None:
                self.progress.emit(done, total)

            results = analyze_pairs(client, slabs, self.config, progress_callback=progress_cb)
            matches = [r for r in results if r.condition_matched]
            self.finished.emit(matches)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Worker failed")
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sticker Slab Scanner")
        self.config = load_config()
        self.worker: ScanWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        btn_layout = QHBoxLayout()
        self.scan_button = QPushButton("Scan Slabs")
        self.scan_button.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        btn_layout.addWidget(self.settings_button)
        layout.addLayout(btn_layout)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Slab name",
                "Sticker name",
                "Slab best buy",
                "Sticker best buy",
                "Diff",
                "Condition",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved_config:
            self.config = dialog.saved_config

    def start_scan(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.status.showMessage("Starting scan...")
        self.scan_button.setEnabled(False)
        self.table.setRowCount(0)
        self.worker = ScanWorker(self.config)
        self.worker.progress.connect(self._update_progress)
        self.worker.error.connect(self._handle_error)
        self.worker.finished.connect(self._scan_finished)
        self.worker.start()

    def _update_progress(self, done: int, total: int) -> None:
        self.status.showMessage(f"Processed {done} of {total}")

    def _handle_error(self, message: str) -> None:
        self.status.showMessage(f"Error: {message}")
        self.scan_button.setEnabled(True)

    def _scan_finished(self, results: List[PairResult]) -> None:
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(result.slab_name))
            self.table.setItem(row, 1, QTableWidgetItem(result.sticker_name))
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(self._format_price(result.slab_buy)),
            )
            self.table.setItem(
                row,
                3,
                QTableWidgetItem(self._format_price(result.sticker_buy)),
            )
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(self._format_price(result.diff)),
            )
            self.table.setItem(row, 5, QTableWidgetItem(result.condition_type or ""))
        self.status.showMessage(
            f"Completed. {len(results)} matches shown." if results else "Completed. No matches."
        )
        self.scan_button.setEnabled(True)

    @staticmethod
    def _format_price(value) -> str:
        if value is None:
            return "-"
        return f"{value:.2f}"


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
