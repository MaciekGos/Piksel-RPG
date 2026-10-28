"""Własny instalator Piksel RPG (kreator w stylu gry) + tryb cichy.

GUI:      python installer/install.py            (albo PikselRPG-Setup.exe zbudowany przez tools/build_windows.py)
Cichy:    python installer/install.py --silent [--dir KATALOG] [--no-shortcuts] [--ollama] [--model llama3.2:3b] [--firewall]
Usuwanie: python installer/install.py --uninstall [--silent] [--purge] [--dir KATALOG]"""
from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
from core import IS_WIN, Installer, InstallError, Options  # noqa: E402
from pikselrpg.i18n import LANGS, detect_language, language, set_language, tr  # noqa: E402


def parse(argv):
    # język (--lang) ustalamy przed zbudowaniem parsera, żeby opisy opcji były w tym języku
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", choices=sorted(LANGS), default=None)
    known, _ = pre.parse_known_args(argv)
    set_language(known.lang or "en")   # instalator domyślnie po angielsku; język zmienia się na pierwszej stronie
    ap = argparse.ArgumentParser(description=tr("Instalator Piksel RPG"))
    ap.add_argument("--silent", action="store_true", help=tr("bez okna, tylko konsola"))
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--purge", action="store_true", help=tr("przy odinstalowaniu usuń też zapisy gier i kronikę"))
    ap.add_argument("--dir", type=Path, default=None)
    ap.add_argument("--no-shortcuts", action="store_true")
    ap.add_argument("--ollama", action="store_true", help=tr("zainstaluj Ollamę, jeśli jej brak (Windows)"))
    ap.add_argument("--model", default=None, help=tr("pobierz model Llamy, np. llama3.2:3b"))
    ap.add_argument("--firewall", action="store_true", help=tr("dodaj regułę zapory (UAC)"))
    ap.add_argument("--lang", choices=sorted(LANGS), default=None, help=tr("język instalatora i gry: pl lub en (domyślnie: en)"))
    a = ap.parse_args(argv)
    a.lang_explicit = a.lang is not None
    a.lang = a.lang or language()
    return a


def cli(a) -> int:
    target = a.dir or core.default_dir()
    if a.uninstall:
        core.uninstall(target, a.purge)
        return 0
    o = Options(target=target, desktop_shortcut=not a.no_shortcuts, start_menu=not a.no_shortcuts,
                install_ollama=a.ollama, pull_model=bool(a.model), model=a.model or core.DEFAULT_MODEL, firewall=a.firewall,
                lang=language())
    try:
        Installer(o, log=print, progress=lambda p: print(f"[{p:3d}%]", end="\r", flush=True)).run()
    except InstallError as e:
        print(tr("BŁĄD: {err}", err=e), file=sys.stderr)
        return 1
    return 0


# ======================================================================== GUI
def gui(a) -> int:
    from PySide6.QtCore import QObject, Qt, QTimer, Signal
    from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                                   QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QStackedWidget, QVBoxLayout, QWidget)
    from pikselrpg import config
    from pikselrpg.ui import theme
    from pikselrpg.ui.app import make_app
    from pikselrpg.ui.widgets import button, card, heading, label

    class Sig(QObject):
        log = Signal(str)
        progress = Signal(int)
        done = Signal(bool, str)

    class Wizard(QMainWindow):
        def __init__(self, uninstall: bool):
            super().__init__()
            self.uninstall_mode = uninstall
            self.sig = Sig()
            self.sig.log.connect(lambda t: self.log.appendPlainText(t))
            self.sig.progress.connect(lambda p: self.bar.setValue(p))
            self.sig.done.connect(self.finished)
            self.setWindowIcon(theme.app_icon())
            self.setFixedSize(760, 560)
            root = QWidget()
            root.setObjectName("root")
            root.setAttribute(Qt.WA_StyledBackground, True)
            self.setCentralWidget(root)
            v = QVBoxLayout(root)
            v.setContentsMargins(30, 22, 30, 20)
            v.setSpacing(12)
            top = QHBoxLayout()
            lg = QLabel()
            lg.setPixmap(theme.logo_pixmap(True, 224))
            top.addWidget(lg)
            top.addStretch(1)
            self.ver = label("", "muted")
            top.addWidget(self.ver)
            v.addLayout(top)
            self.stack = QStackedWidget()
            v.addWidget(self.stack, 1)
            nav = QHBoxLayout()
            self.cancel = button("", None, "ghost")
            self.cancel.clicked.connect(self.close)
            self.back = button("", "arrow-left", "")
            self.back.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
            self.next = button("", "play-circle", "primary")
            self.next.clicked.connect(self.on_next)
            nav.addWidget(self.cancel)
            nav.addStretch(1)
            nav.addWidget(self.back)
            nav.addWidget(self.next)
            v.addLayout(nav)
            self.running = False
            self.build_pages()
            self.retitle()
            self.go(0)

        def retitle(self):
            self.setWindowTitle(tr("Odinstaluj {app}", app=config.APP_TITLE) if self.uninstall_mode
                                else tr("Instalator – {app}", app=config.APP_TITLE))
            self.ver.setText(tr("wersja {version}", version=config.APP_VERSION))
            self.cancel.setText(tr("Anuluj"))
            self.back.setText(tr("Wstecz"))

        def language_box(self):
            """Wybór języka na pierwszej stronie; zmiana przebudowuje kreator od razu."""
            row = QHBoxLayout()
            row.addWidget(label(tr("Język:"), "muted"))
            self.lang_box = QComboBox()
            for code, name in LANGS.items():
                self.lang_box.addItem(name, code)
            self.lang_box.setCurrentIndex(self.lang_box.findData(language()))
            self.lang_box.currentIndexChanged.connect(lambda _i: QTimer.singleShot(0, self.change_language))
            row.addWidget(self.lang_box)
            row.addStretch(1)
            return row

        def change_language(self):
            code = self.lang_box.currentData()
            if code == language():
                return
            set_language(code)
            st = {"path": self.path.text(), "desk": self.c_desk.isChecked(), "menu": self.c_menu.isChecked(),
                  "oll": self.c_oll.isChecked(), "mod": self.c_mod.isChecked(), "model": self.model.currentIndex(),
                  "fw": self.c_fw.isChecked(), "purge": self.purge.isChecked() if self.uninstall_mode else False}
            idx = self.stack.currentIndex()
            while self.stack.count():
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
                w.deleteLater()
            self.build_pages()
            self.path.setText(st["path"])
            self.c_desk.setChecked(st["desk"])
            self.c_menu.setChecked(st["menu"])
            self.c_oll.setChecked(st["oll"])
            self.c_mod.setChecked(st["mod"])
            self.model.setCurrentIndex(st["model"])
            self.c_fw.setChecked(st["fw"])
            if self.uninstall_mode:
                self.purge.setChecked(st["purge"])
            self.retitle()
            self.go(idx)

        # ---------------------------------------------------------- strony
        def build_pages(self):
            # 0: powitanie
            w0 = QWidget()
            l0 = QVBoxLayout(w0)
            l0.addLayout(self.language_box())
            if self.uninstall_mode:
                l0.addWidget(heading("trash", tr("Odinstalować Piksel RPG?"), "h2"))
                l0.addWidget(label(tr("Usunę program z tego komputera: pliki, skróty i wpis w „Aplikacje i funkcje”."), "", True))
                self.purge = QCheckBox(tr("Usuń też zapisy gier i kronikę „kto był kim” z tego komputera"))
                l0.addWidget(self.purge)
                l0.addWidget(label(tr("Bez tej opcji Twoje kampanie zostaną i będzie można do nich wrócić po ponownej instalacji. "
                                      "Ollama i pobrane modele Llamy nie są usuwane."), "muted", True))
            else:
                l0.addWidget(heading("sword", tr("Witaj w Piksel RPG"), "h2"))
                l0.addWidget(label(tr("Kooperacyjne RPG z Mistrzem Gry AI. Jedna osoba hostuje grę i uruchamia Llamę lokalnie, "
                                      "reszta dołącza kodem zaproszenia — bez serwerów, kont i opłat. Zapisy gry trzyma każdy "
                                      "uczestnik u siebie, więc kampanię można wznowić u dowolnego z graczy."), "", True))
                l0.addWidget(label(tr("Instalacja odbywa się w Twoim profilu — nie potrzebujesz praw administratora."), "muted", True))
            l0.addStretch(1)
            self.stack.addWidget(w0)

            # 1: opcje
            w1 = QWidget()
            l1 = QVBoxLayout(w1)
            l1.addWidget(heading("gear", tr("Opcje instalacji"), "h2"))
            c, cl = card()
            cl.addWidget(label(tr("Katalog instalacji"), "muted"))
            r = QHBoxLayout()
            self.path = QLineEdit(str(core.default_dir()))
            r.addWidget(self.path, 1)
            b = button(tr("Wybierz…"), "folder-open", "")
            b.clicked.connect(self.pick)
            r.addWidget(b)
            cl.addLayout(r)
            self.c_desk = QCheckBox(tr("Skrót na pulpicie"))
            self.c_desk.setChecked(True)
            self.c_menu = QCheckBox(tr("Skrót w menu Start"))
            self.c_menu.setChecked(True)
            cl.addWidget(self.c_desk)
            cl.addWidget(self.c_menu)
            l1.addWidget(c)
            c2, c2l = card()
            c2l.addWidget(heading("cpu", tr("Llama (tylko dla hosta)")))
            have = core.find_ollama() is not None or core.ollama_running()
            self.c_oll = QCheckBox(tr("Zainstaluj Ollamę — lokalny silnik Llamy (już zainstalowana)") if have
                                 else tr("Zainstaluj Ollamę — lokalny silnik Llamy"))
            self.c_oll.setChecked(not have and IS_WIN)
            self.c_oll.setEnabled(not have and IS_WIN)
            self.c_mod = QCheckBox(tr("Pobierz model Llamy:"))
            self.c_mod.setChecked(IS_WIN)
            self.model = QComboBox()
            for m, desc in config.recommended_models():
                self.model.addItem(desc, m)
            mr = QHBoxLayout()
            mr.addWidget(self.c_mod)
            mr.addWidget(self.model, 1)
            c2l.addWidget(self.c_oll)
            c2l.addLayout(mr)
            c2l.addWidget(label(tr("Gracze, którzy tylko dołączają, nie potrzebują Ollamy ani modelu. Możesz też to zrobić później "
                                   "w Ustawieniach aplikacji. Tryb demo działa bez AI."), "muted", True))
            self.c_fw = QCheckBox(tr("Dodaj regułę zapory dla portu {port} (wymaga zgody UAC; opcjonalne)", port=config.DEFAULT_PORT))
            self.c_fw.setVisible(IS_WIN)
            c2l.addWidget(self.c_fw)
            l1.addWidget(c2)
            l1.addStretch(1)
            self.stack.addWidget(w1)

            # 2: postęp
            w2 = QWidget()
            l2 = QVBoxLayout(w2)
            self.h_prog = heading("hourglass", tr("Odinstalowuję…") if self.uninstall_mode else tr("Instaluję…"), "h2")
            l2.addWidget(self.h_prog)
            self.bar = QProgressBar()
            self.bar.setRange(0, 100)
            l2.addWidget(self.bar)
            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setStyleSheet("font-family: Consolas, 'DejaVu Sans Mono', monospace; font-size: 12px;")
            l2.addWidget(self.log, 1)
            self.stack.addWidget(w2)

            # 3: koniec
            w3 = QWidget()
            l3 = QVBoxLayout(w3)
            self.end_head = heading("check-circle", tr("Gotowe"), "h2")
            l3.addWidget(self.end_head)
            self.end_text = label("", "", True)
            l3.addWidget(self.end_text)
            self.c_run = QCheckBox(tr("Uruchom Piksel RPG"))
            self.c_run.setChecked(True)
            l3.addWidget(self.c_run)
            l3.addStretch(1)
            self.stack.addWidget(w3)

        def pick(self):
            d = QFileDialog.getExistingDirectory(self, tr("Katalog instalacji"), self.path.text())
            if d:
                self.path.setText(str(Path(d) / (core.APP_NAME if not (Path(d) / "install.json").exists() else "")))

        # ---------------------------------------------------------- nawigacja
        def go(self, i: int):
            i = max(0, i)
            self.stack.setCurrentIndex(i)
            self.back.setVisible(i == 1)
            self.cancel.setEnabled(not self.running)
            labels = {0: tr("Odinstaluj") if self.uninstall_mode else tr("Dalej"), 1: tr("Zainstaluj"), 2: tr("Czekaj…"), 3: tr("Zakończ")}
            self.next.setText(labels[i])
            self.next.setEnabled(i != 2)

        def on_next(self):
            i = self.stack.currentIndex()
            if i == 0:
                self.start_uninstall() if self.uninstall_mode else self.go(1)
            elif i == 1:
                self.start_install()
            elif i == 3:
                if self.c_run.isChecked() and not self.uninstall_mode and self.launch:
                    subprocess.Popen(self.launch, cwd=self.path.text(), close_fds=True)
                self.close()

        def closeEvent(self, e):
            if self.running:
                e.ignore()
                return
            super().closeEvent(e)

        # ---------------------------------------------------------- praca w tle
        def worker(self, fn):
            self.running = True
            self.go(2)
            self.log.clear()

            def run():
                try:
                    fn()
                    self.sig.done.emit(True, "")
                except InstallError as e:
                    self.sig.done.emit(False, str(e))
                except Exception as e:  # nieoczekiwane
                    self.sig.done.emit(False, tr("{type}: {err}", type=type(e).__name__, err=e))

            threading.Thread(target=run, daemon=True).start()

        def start_install(self):
            o = Options(target=Path(self.path.text().strip()), desktop_shortcut=self.c_desk.isChecked(),
                        start_menu=self.c_menu.isChecked(), install_ollama=self.c_oll.isChecked(),
                        pull_model=self.c_mod.isChecked(), model=self.model.currentData(), firewall=self.c_fw.isChecked(),
                        lang=language())
            self.inst = Installer(o, log=self.sig.log.emit, progress=self.sig.progress.emit)
            self.launch = None
            self.worker(self.inst.run)

        def start_uninstall(self):
            target = a.dir or core.default_dir()
            self.launch = None
            self.worker(lambda: core.uninstall(target, self.purge.isChecked(), self.sig.log.emit))

        def finished(self, ok: bool, err: str):
            self.running = False
            self.cancel.setEnabled(True)
            if ok:
                self.launch = None if self.uninstall_mode else self.inst.launch_command()
                self.end_text.setText(tr("Piksel RPG został usunięty z tego komputera.") if self.uninstall_mode else
                                      tr("Piksel RPG jest zainstalowany. Znajdziesz go w menu Start / na pulpicie. "
                                         "Aby zagrać z innymi, jedna osoba wybiera „Hostuj nową grę”, a pozostałe „Dołącz do gry” "
                                         "z kodem zaproszenia."))
                self.c_run.setVisible(not self.uninstall_mode)
            else:
                self.end_head.deleteLater()
                self.end_head = heading("warning", tr("Coś poszło nie tak"), "h2")
                self.stack.widget(3).layout().insertWidget(0, self.end_head)
                self.end_text.setText(tr("{err}\n\nSzczegóły są w dzienniku na poprzednim ekranie. Możesz zamknąć instalator i spróbować ponownie.", err=err))
                self.c_run.setVisible(False)
            self.go(3)

    app = make_app([])
    w = Wizard(a.uninstall)
    if a.dir:
        w.path.setText(str(a.dir))
    w.show()
    return app.exec()


def main(argv=None) -> int:
    a = parse(sys.argv[1:] if argv is None else argv)
    if a.uninstall and not a.lang_explicit:      # odinstalowanie w języku wybranym przy instalacji
        try:
            import json
            m = json.loads(((a.dir or core.default_dir()) / "install.json").read_text(encoding="utf-8"))
            if m.get("lang") in LANGS:
                set_language(m["lang"])
        except (OSError, ValueError):
            pass
    if a.silent:
        return cli(a)
    return gui(a)


if __name__ == "__main__":
    sys.exit(main())
