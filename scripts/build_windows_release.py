"""
Build & Packaging script for FlightDeck on Windows.
Produces a complete Windows Setup installer (dist/FlightDeck-Setup.exe) using PyInstaller and Inno Setup.
"""
import os
import sys
import shutil
import subprocess

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_ico():
    """Generates assets/icon.ico from assets/icon.png if needed."""
    png_path = os.path.join(PROJECT_ROOT, "assets", "icon.png")
    ico_path = os.path.join(PROJECT_ROOT, "assets", "icon.ico")
    if os.path.exists(ico_path):
        return ico_path
    if not os.path.exists(png_path):
        return None
    try:
        from PIL import Image
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"Generated {ico_path}")
        return ico_path
    except Exception as e:
        print(f"Pillow not available to generate icon.ico ({e}), skipping ICO creation.")
        return None


def find_iscc() -> str:
    """Finds the Inno Setup Compiler (ISCC.exe) executable."""
    # 1. Check PATH
    iscc = shutil.which("iscc") or shutil.which("iscc.exe") or shutil.which("ISCC.exe")
    if iscc:
        return iscc

    # 2. Check environment variable
    custom_dir = os.environ.get("INNO_SETUP_DIR")
    if custom_dir:
        cand = os.path.join(custom_dir, "ISCC.exe")
        if os.path.isfile(cand):
            return cand

    # 3. Check well-known installation paths
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    return ""


def resolve_version() -> str:
    """Resolves release version from CLI args, env var, or core/domain/models.py."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip().lstrip("v")
    env_ver = os.environ.get("RELEASE_TAG") or os.environ.get("VERSION")
    if env_ver and env_ver.strip():
        return env_ver.strip().lstrip("v")
    models_path = os.path.join(PROJECT_ROOT, "core", "domain", "models.py")
    if os.path.exists(models_path):
        import re
        with open(models_path, "r", encoding="utf-8") as f:
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
            if m:
                return m.group(1).lstrip("v")
    return "1.0.5"


def build():
    os.chdir(PROJECT_ROOT)
    version = resolve_version()
    print(f"Building FlightDeck Windows release v{version}...")

    ico_path = ensure_ico()

    # Step 1: Build standalone binaries with PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=FlightDeck",
        "--add-data", f"assets{os.pathsep}assets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=tzdata",
        "--hidden-import=zoneinfo",
        "--exclude-module=ui.macos",
        "main.py"
    ]
    if ico_path and os.path.exists(ico_path):
        cmd.extend(["--icon", ico_path])

    print("Running PyInstaller command:")
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

    dist_dir = os.path.join(PROJECT_ROOT, "dist", "FlightDeck")
    if not os.path.isdir(dist_dir):
        raise RuntimeError(f"PyInstaller build directory not found: {dist_dir}")

    # Copy launcher helper script to dist directory
    run_bat = os.path.join(PROJECT_ROOT, "scripts", "run_windows.bat")
    if os.path.exists(run_bat):
        shutil.copyfile(run_bat, os.path.join(dist_dir, "run_windows.bat"))

    # Step 2: Compile Inno Setup installer
    iscc = find_iscc()
    iss_file = os.path.join(PROJECT_ROOT, "packaging", "windows", "flightdeck.iss")

    if not iscc:
        msg = (
            "⚠️ Inno Setup Compiler (ISCC.exe) not found!\n"
            "To build the Windows installer (FlightDeck-Setup.exe), please install Inno Setup:\n"
            "  choco install innosetup\n"
            "  or winget install JRSoftware.InnoSetup\n"
        )
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            raise RuntimeError(msg)
        else:
            print(msg)
            print("PyInstaller output preserved in dist/FlightDeck.")
            return

    print(f"Compiling Inno Setup installer with {iscc}...")
    iscc_cmd = [
        iscc,
        f"/DAppVersion={version}",
        iss_file
    ]
    print("Running ISCC command:")
    print(" ".join(iscc_cmd))
    subprocess.run(iscc_cmd, check=True)

    setup_exe = os.path.join(PROJECT_ROOT, "dist", "FlightDeck-Setup.exe")
    if not os.path.exists(setup_exe):
        raise RuntimeError(f"Expected installer executable not found at {setup_exe}")

    print(f"[SUCCESS] Successfully built FlightDeck Windows installer: {setup_exe}")


if __name__ == "__main__":
    build()
