from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal


class CommandWorker(QObject):
    output_received = Signal(str)
    finished = Signal(int)
    started = Signal()

    def __init__(self, project_root: Path, python_exe: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project_root = project_root
        self.python_exe = python_exe
        self.process: QProcess | None = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def cancel(self) -> bool:
        if not self.is_running() or self.process is None:
            return False
        self.output_received.emit("Devam eden işlem kullanıcı isteğiyle iptal ediliyor.\n")
        self.process.terminate()
        if not self.process.waitForFinished(2500):
            self.process.kill()
        return True

    def run(self, args: list[str]) -> None:
        if self.is_running():
            self.output_received.emit("Bir işlem zaten çalışıyor. Lütfen bitmesini bekleyin.\n")
            return

        if not self.python_exe.exists():
            self.output_received.emit(
                "Python sanal ortamı bulunamadı. Lütfen masaüstü kısayolunu yeniden açın "
                "veya start_cyzella.bat çalıştırın.\n"
            )
            self.finished.emit(1)
            return

        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(self.project_root))
        self.process.setProgram(str(self.python_exe))
        self.process.setArguments(args)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.started.emit()
        self.process.start()

    def _read_output(self) -> None:
        if self.process is None:
            return
        data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output_received.emit(data)

    def _finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._read_output()
        self.finished.emit(exit_code)

    def _process_error(self, error: QProcess.ProcessError) -> None:
        self.output_received.emit(f"Komut çalıştırılamadı. Teknik detay: {error.name}\n")
