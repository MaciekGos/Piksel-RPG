"""Logika instalatora Piksel RPG (bez GUI — można ją testować i używać z linii poleceń).

Dwa tryby (wybierane automatycznie):
  * "frozen" — instalator zbudowany PyInstallerem z gotową aplikacją w payload.zip (Windows, bez Pythona u gracza),
  * "source" — instalator uruchomiony ze źródeł: kopiuje kod, tworzy venv i doinstalowuje PySide6 przez pip.

Wszystko działa w profilu użytkownika, bez uprawnień administratora (poza opcjonalną regułą zapory)."""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

APP_NAME = "PikselRPG"
APP_TITLE = "Piksel RPG"
IS_WIN = sys.platform == "win32"
FROZEN = bool(getattr(sys, "frozen", False))
PROJECT = Path(__file__).resolve().parent.parent
RES = Path(getattr(sys, "_MEIPASS", PROJECT / "installer"))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from pikselrpg.config import APP_VERSION, DEFAULT_MODEL, DEFAULT_PORT, OLLAMA_URL  # noqa: E402
from pikselrpg.i18n import set_language, tr  # noqa: E402
from pikselrpg.llm import OllamaClient, OllamaError  # noqa: E402

OLLAMA_URL_DL = "https://ollama.com/download/OllamaSetup.exe"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PikselRPG"


class InstallError(Exception):
    pass


def default_dir() -> Path:
    if IS_WIN:
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME
    return Path.home() / ".local" / "share" / f"{APP_NAME}-app"


def user_data_dir() -> Path:
    from pikselrpg.config import default_home
    return default_home()


def find_ollama() -> str | None:
    p = shutil.which("ollama")
    if p:
        return p
    if IS_WIN:
        c = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if c.exists():
            return str(c)
    return None


def ollama_running() -> bool:
    return OllamaClient(OLLAMA_URL).ping()


@dataclass
class Options:
    target: Path = field(default_factory=default_dir)
    desktop_shortcut: bool = True
    start_menu: bool = True
    install_ollama: bool = False
    pull_model: bool = False
    model: str = DEFAULT_MODEL
    firewall: bool = False
    port: int = DEFAULT_PORT
    purge_data: bool = False
    lang: str = ""          # "pl" / "en"; puste = nie zmieniaj (bieżący język i18n)


def psq(s: str) -> str:
    """Literał tekstowy PowerShell (apostrofy)."""
    return "'" + str(s).replace("'", "''") + "'"


def run_ps(script: str, timeout: int = 60) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise InstallError((r.stderr or r.stdout or tr("błąd PowerShell")).strip()[:400])
    return r.stdout.strip()


# ====================================================================== payload
def build_source_payload(dst: Path) -> Path:
    skip = {"__pycache__", ".pytest_cache"}
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for base in ("pikselrpg",):
            for f in (PROJECT / base).rglob("*"):
                if f.is_file() and not (set(f.parts) & skip) and f.suffix != ".pyc":
                    z.write(f, f.relative_to(PROJECT).as_posix())
        for name in ("main.py", "requirements.txt", "README.md"):
            if (PROJECT / name).exists():
                z.write(PROJECT / name, name)
        for f in (PROJECT / "installer").glob("*.py"):
            z.write(f, f"installer/{f.name}")
    return dst


def payload() -> tuple[str, Path | None]:
    """(tryb, ścieżka zip). Tryb frozen wymaga payload.zip dołączonego do instalatora."""
    z = RES / "payload.zip"
    if FROZEN:
        if not z.exists():
            raise InstallError(tr("Instalator jest uszkodzony: brak payload.zip."))
        return "frozen", z
    return "source", None


# ====================================================================== instalacja
class Installer:
    def __init__(self, opts: Options, log: Callable[[str], None] = print, progress: Callable[[int], None] = lambda p: None):
        self.o = opts
        self.log = log
        self.progress = progress
        self.mode = "source"
        self.created: dict = {"shortcuts": []}
        self._base = 0.0

    # ---- postęp
    def _span(self, start: float, end: float) -> Callable[[float], None]:
        return lambda f: self.progress(int(start + (end - start) * max(0.0, min(1.0, f))))

    def run(self) -> None:
        o = self.o
        if o.lang:
            set_language(o.lang)
        steps: list[tuple[str, Callable[[Callable[[float], None]], None], float]] = [
            (tr("Przygotowanie katalogu"), self.step_prepare, 3),
            (tr("Kopiowanie plików"), self.step_extract, 12),
        ]
        self.mode, _ = payload()
        if self.mode == "source":
            steps.append((tr("Tworzenie środowiska Python i instalacja PySide6"), self.step_venv, 35))
        steps.append((tr("Skróty i rejestracja programu"), self.step_integrate, 5))
        if o.firewall and IS_WIN:
            steps.append((tr("Reguła zapory sieciowej"), self.step_firewall, 3))
        if o.install_ollama:
            steps.append((tr("Instalacja Ollamy (silnika Llamy)"), self.step_ollama, 20))
        if o.pull_model:
            steps.append((tr("Pobieranie modelu {model}", model=o.model), self.step_model, 40))
        total = sum(w for _, _, w in steps)
        done = 0.0
        for title, fn, w in steps:
            self.log("▶ " + title)
            fn(self._span(done / total * 100, (done + w) / total * 100))
            done += w
            self.progress(int(done / total * 100))
        self.write_manifest()
        self.progress(100)
        self.log("✔ " + tr("Gotowe."))

    # ---- kroki
    def step_prepare(self, prog) -> None:
        t = self.o.target
        if t.exists() and any(t.iterdir()):
            if not (t / "install.json").exists():
                raise InstallError(tr("Katalog {path} nie jest pusty i nie wygląda na instalację Piksel RPG — wybierz inny.", path=t))
            self.log("  " + tr("Znaleziono poprzednią instalację — aktualizuję pliki (zapisy gier zostają)."))
            self._remove_app_files(keep_venv=True)
        try:
            t.mkdir(parents=True, exist_ok=True)
            (t / ".write-test").write_text("x")
            (t / ".write-test").unlink()
        except OSError as e:
            raise InstallError(tr("Nie mogę zapisać w {path}: {err}", path=t, err=e)) from None

    def step_extract(self, prog) -> None:
        mode, zpath = payload()
        tmp = None
        if zpath is None:
            tmp = Path(tempfile.mkdtemp()) / "payload.zip"
            zpath = build_source_payload(tmp)
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            for i, n in enumerate(names):
                z.extract(n, self.o.target)
                prog((i + 1) / len(names))
        if tmp:
            shutil.rmtree(tmp.parent, ignore_errors=True)
        if FROZEN:
            dst = self.o.target / ("Uninstall.exe" if IS_WIN else "Uninstall")
            shutil.copy2(sys.executable, dst)
        self.log("  " + tr("Skopiowano {n} plików do {path}", n=len(names), path=self.o.target))

    def venv_python(self) -> Path:
        v = self.o.target / "venv"
        return v / ("Scripts/python.exe" if IS_WIN else "bin/python")

    def venv_pythonw(self) -> Path:
        v = self.o.target / "venv"
        return v / "Scripts/pythonw.exe" if IS_WIN else v / "bin/python"

    def step_venv(self, prog) -> None:
        venv = self.o.target / "venv"
        if not self.venv_python().exists():
            self.log("  " + tr("Tworzę środowisko wirtualne…"))
            r = subprocess.run([sys.executable, "-m", "venv", str(venv)], capture_output=True, text=True, creationflags=NO_WINDOW)
            if r.returncode:
                raise InstallError(tr("Nie udało się utworzyć venv: {err}", err=(r.stderr or r.stdout)[-300:]))
        prog(0.15)
        self.log("  " + tr("Instaluję PySide6 (pip, ok. 150 MB — chwilę potrwa)…"))
        cmd = [str(self.venv_python()), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
               "-r", str(self.o.target / "requirements.txt")]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=NO_WINDOW)
        n = 0
        tail: list[str] = []
        for line in p.stdout:
            line = line.rstrip()
            if line:
                tail = (tail + [line])[-8:]
                n += 1
                if line.startswith(("Collecting", "Downloading", "Installing", "Successfully")):
                    self.log("  " + line[:110])
                prog(min(0.95, 0.15 + n / 60))
        if p.wait():
            raise InstallError(tr("pip nie zainstalował PySide6 (brak internetu?):\n{tail}", tail="\n".join(tail)))

    def launch_command(self) -> list[str]:
        if self.mode == "frozen" or FROZEN:
            return [str(self.o.target / ("PikselRPG.exe" if IS_WIN else "PikselRPG"))]
        return [str(self.venv_pythonw()), str(self.o.target / "main.py")]

    def uninstall_command(self) -> list[str]:
        if FROZEN:
            return [str(self.o.target / ("Uninstall.exe" if IS_WIN else "Uninstall")), "--uninstall"]
        return [str(self.venv_pythonw()), str(self.o.target / "installer" / "install.py"), "--uninstall", "--dir", str(self.o.target)]

    def icon_path(self) -> Path:
        if self.mode == "frozen":      # ikona jest wbudowana w PikselRPG.exe (PyInstaller --icon)
            return Path(self.launch_command()[0])
        return self.o.target / "pikselrpg" / "assets" / "icon.ico"

    def step_integrate(self, prog) -> None:
        cmd = self.launch_command()
        if IS_WIN:
            self._shortcuts_windows(cmd)
            self._register_windows()
        elif sys.platform.startswith("linux"):
            self._desktop_entry_linux(cmd)
        else:
            self.log("  " + tr("(Ta platforma: bez skrótów — uruchom ręcznie: {cmd})", cmd=" ".join(cmd)))
        self.write_profile_lang()

    # ---- Windows
    def _shortcuts_windows(self, cmd: list[str]) -> None:
        target, args = cmd[0], subprocess.list2cmdline(cmd[1:])
        icon = str(self.icon_path())
        targets: list[str] = []
        if self.o.start_menu:
            targets.append(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", APP_TITLE, f"{APP_TITLE}.lnk"))
        desk = run_ps("[Environment]::GetFolderPath('Desktop')") if self.o.desktop_shortcut else ""
        if desk:
            targets.append(os.path.join(desk, f"{APP_TITLE}.lnk"))
        for lnk in targets:
            Path(lnk).parent.mkdir(parents=True, exist_ok=True)
            run_ps(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({psq(lnk)});"
                   f"$s.TargetPath={psq(target)};$s.Arguments={psq(args)};$s.WorkingDirectory={psq(str(self.o.target))};"
                   f"$s.IconLocation={psq(icon)};$s.Description={psq(tr("Kooperacyjne RPG z Mistrzem Gry AI"))};$s.Save()")
            self.created["shortcuts"].append(lnk)
            self.log("  " + tr("Skrót: {path}", path=lnk))

    def _register_windows(self) -> None:
        import winreg
        unin = subprocess.list2cmdline(self.uninstall_command())
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
            for name, val in (("DisplayName", APP_TITLE), ("DisplayVersion", APP_VERSION), ("Publisher", "Piksel RPG"),
                              ("InstallLocation", str(self.o.target)), ("DisplayIcon", str(self.icon_path())),
                              ("UninstallString", unin)):
                winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
            winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
        self.log("  " + tr("Zarejestrowano w „Aplikacje i funkcje” (Ustawienia Windows)."))

    def step_firewall(self, prog) -> None:
        args = f"advfirewall firewall add rule name=PikselRPG dir=in action=allow protocol=TCP localport={self.o.port} profile=private,public"
        self.log("  " + tr("Zaraz pojawi się okno kontroli konta (UAC) — potwierdź, aby dodać regułę zapory."))
        try:
            run_ps(f"Start-Process netsh -ArgumentList {psq(args)} -Verb RunAs -Wait", timeout=120)
            self.created["firewall"] = self.o.port
        except Exception as e:
            self.log("  ⚠ " + tr("Nie dodano reguły zapory ({err}). Windows zapyta o zgodę przy pierwszym hostowaniu.", err=e))

    # ---- Linux
    def _desktop_entry_linux(self, cmd: list[str]) -> None:
        ico = self.o.target / "pikselrpg" / "assets" / "icon.png"
        entry = (f"[Desktop Entry]\nType=Application\nName={APP_TITLE}\nComment={tr('Kooperacyjne RPG z Mistrzem Gry AI')}\n"
                 f"Exec={' '.join(shlex.quote(c) for c in cmd)}\n"
                 f"Path={self.o.target}\nIcon={ico}\nTerminal=false\nCategories=Game;RolePlaying;\n")
        paths = []
        if self.o.start_menu:
            paths.append(Path.home() / ".local/share/applications" / f"{APP_NAME}.desktop")
        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(entry, encoding="utf-8")
            p.chmod(0o755)
            self.created["shortcuts"].append(str(p))
            self.log("  " + tr("Wpis menu: {path}", path=p))

    # ---- Ollama
    def step_ollama(self, prog) -> None:
        if ollama_running() or find_ollama():
            self.log("  " + tr("Ollama jest już zainstalowana — pomijam."))
            return
        if not IS_WIN:
            self.log("  " + tr("Zainstaluj Ollamę ręcznie: https://ollama.com/download (Linux: curl -fsSL https://ollama.com/install.sh | sh)"))
            return
        exe = Path(tempfile.mkdtemp()) / "OllamaSetup.exe"
        self.log("  " + tr("Pobieram instalator Ollamy z ollama.com…"))
        req = urllib.request.Request(OLLAMA_URL_DL, headers={"User-Agent": "PikselRPG-Setup"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r, open(exe, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                got = 0
                while chunk := r.read(1 << 16):
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        prog(0.8 * got / total)
        except OSError as e:
            raise InstallError(tr("Nie udało się pobrać Ollamy: {err}. Zainstaluj ją ręcznie z ollama.com.", err=e)) from None
        self.log("  " + tr("Instaluję Ollamę (po cichu)…"))
        r = subprocess.run([str(exe), "/SILENT", "/NORESTART"], timeout=900)
        prog(0.95)
        if r.returncode not in (0, None):
            raise InstallError(tr("Instalator Ollamy zakończył się kodem {code}.", code=r.returncode))
        t = time.time()
        while time.time() - t < 45 and not ollama_running():
            if time.time() - t > 8 and find_ollama():
                subprocess.Popen([find_ollama(), "serve"], creationflags=NO_WINDOW | 0x00000008, close_fds=True)
                t += 20
            time.sleep(1.5)
        self.log("  " + tr("Ollama działa.") if ollama_running() else
                 "  ⚠ " + tr("Ollama jest zainstalowana, ale jeszcze nie odpowiada — uruchom ją z menu Start."))

    def step_model(self, prog) -> None:
        cl = OllamaClient(OLLAMA_URL, self.o.model)
        t = time.time()
        while not cl.ping():
            if time.time() - t > 30:
                self.log("  ⚠ " + tr("Ollama nie odpowiada — model pobierzesz później w Ustawieniach aplikacji."))
                return
            time.sleep(1.5)
        last = [""]

        def cb(status: str, done: int, total: int) -> None:
            if total:
                prog(done / total)
            if status != last[0] and not total:
                last[0] = status
                self.log("  " + status)

        try:
            cl.pull(self.o.model, cb)
        except OllamaError as e:
            self.log("  ⚠ " + tr("Nie pobrano modelu: {err}. Zrobisz to później w Ustawieniach aplikacji.", err=e))
            return
        self.log("  " + tr("Model {model} gotowy.", model=self.o.model))

    # ---- język gry
    def write_profile_lang(self) -> None:
        """Zapisuje wybrany język w profilu gry (profile.json); istniejące pola zostają."""
        lang = self.o.lang
        if not lang:
            return
        try:
            f = user_data_dir() / "profile.json"
            prof: dict = {}
            if f.exists():
                try:
                    prof = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    prof = {}
                if not isinstance(prof, dict):
                    prof = {}
            prof["lang"] = lang
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(prof, ensure_ascii=False), encoding="utf-8")
            self.log("  " + tr("Język gry: {lang}", lang=lang))
        except OSError as e:
            self.log("  ⚠ " + tr("Nie zapisano języka w profilu gry ({err}) — można go zmienić w Ustawieniach aplikacji.", err=e))

    # ---- manifest / odinstalowanie
    def write_manifest(self) -> None:
        (self.o.target / "install.json").write_text(json.dumps({
            "version": APP_VERSION, "mode": self.mode, "shortcuts": self.created["shortcuts"],
            "firewall": self.created.get("firewall"), "lang": self.o.lang or None, "installed": time.time()}, ensure_ascii=False, indent=1), encoding="utf-8")

    def _remove_app_files(self, keep_venv: bool = False) -> None:
        for child in self.o.target.iterdir():
            if keep_venv and child.name == "venv":
                continue
            if child.name == "install.json":
                continue
            shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)


def uninstall(target: Path, purge_data: bool, log: Callable[[str], None] = print) -> None:
    man = target / "install.json"
    info = json.loads(man.read_text(encoding="utf-8")) if man.exists() else {}
    for lnk in info.get("shortcuts", []):
        try:
            Path(lnk).unlink(missing_ok=True)
            if IS_WIN and Path(lnk).parent.name == APP_TITLE:
                Path(lnk).parent.rmdir()
            log("  " + tr("Usunięto skrót: {path}", path=lnk))
        except OSError:
            pass
    if IS_WIN:
        try:
            import winreg
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        except OSError:
            pass
        if info.get("firewall"):
            try:
                run_ps("Start-Process netsh -ArgumentList 'advfirewall firewall delete rule name=PikselRPG' -Verb RunAs -Wait", timeout=120)
            except Exception:
                log("  ⚠ " + tr("Nie usunięto reguły zapory (możesz ją skasować ręcznie: „PikselRPG”)."))
    if purge_data:
        d = user_data_dir()
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            log("  " + tr("Usunięto zapisy gier i kronikę: {path}", path=d))
    else:
        log("  " + tr("Zapisy gier i kronika zostały zachowane ({path}).", path=user_data_dir()))
    if IS_WIN and Path(sys.executable).is_relative_to(target):
        # uruchomiony z katalogu instalacji — usuń po zakończeniu procesu
        subprocess.Popen(["cmd", "/c", f'ping -n 4 127.0.0.1 >nul & rmdir /s /q "{target}"'],
                         creationflags=NO_WINDOW | 0x00000008, close_fds=True)
        log("  " + tr("Katalog programu zostanie usunięty za chwilę."))
    else:
        shutil.rmtree(target, ignore_errors=True)
        log("  " + tr("Usunięto {path}", path=target))
