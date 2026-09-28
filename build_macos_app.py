import os
import sys
import shutil
import subprocess

APP_NAME = "FlightDeck.app"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(PROJECT_DIR, APP_NAME)
CONTENTS_DIR = os.path.join(APP_DIR, "Contents")
MACOS_DIR = os.path.join(CONTENTS_DIR, "MacOS")
RESOURCES_DIR = os.path.join(CONTENTS_DIR, "Resources")

def generate_icns():
    print("🎨 Generating ICNS icon from assets/icon.png...")
    icon_src = os.path.join(PROJECT_DIR, "assets", "icon.png")
    if not os.path.exists(icon_src):
        from scripts.generate_app_icon import create_app_icon
        create_app_icon(icon_src, 1024)

    iconset_dir = os.path.join(PROJECT_DIR, "assets", "AppIcon.iconset")
    os.makedirs(iconset_dir, exist_ok=True)

    sizes = [16, 32, 128, 256, 512]
    for sz in sizes:
        # Standard 1x
        out_1x = os.path.join(iconset_dir, f"icon_{sz}x{sz}.png")
        subprocess.run(["sips", "-z", str(sz), str(sz), icon_src, "--out", out_1x], capture_output=True)
        # Retina 2x
        out_2x = os.path.join(iconset_dir, f"icon_{sz}x{sz}@2x.png")
        subprocess.run(["sips", "-z", str(sz * 2), str(sz * 2), icon_src, "--out", out_2x], capture_output=True)

    # Generate ICNS. Some macOS releases reject otherwise valid iconsets from
    # `sips`; retain the checked-in icon instead of preventing an app rebuild.
    icns_path = os.path.join(PROJECT_DIR, "assets", "AppIcon.icns")
    result = subprocess.run(
        ["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if not os.path.exists(icns_path):
            raise subprocess.CalledProcessError(
                result.returncode, result.args, output=result.stdout, stderr=result.stderr
            )
        print("⚠️  iconutil rejected the generated iconset; using existing AppIcon.icns.")
    shutil.rmtree(iconset_dir, ignore_errors=True)
    print(f"✅ AppIcon.icns successfully generated: {icns_path}")
    return icns_path

def check_python_code():
    print("🧪 Verifying and validating Python code syntax...")
    import py_compile

    py_files = []
    for root, _, files in os.walk(PROJECT_DIR):
        if any(x in root for x in [".git", "FlightDeck.app", "__pycache__", "deb_dist", "dmg_temp"]):
            continue
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))

    for py_file in py_files:
        try:
            py_compile.compile(py_file, doraise=True)
            print(f"  ✓ {os.path.relpath(py_file, PROJECT_DIR)}: Syntax OK")
        except py_compile.PyCompileError as e:
            print(f"  ❌ SYNTAX ERROR in {py_file}: {e}")
            raise SystemExit(1)

    # Verify module imports
    try:
        import sys
        if PROJECT_DIR not in sys.path:
            sys.path.insert(0, PROJECT_DIR)
        import core.domain
        import core.services
        import core.providers
        import core.config_manager
        import core.calendar_scanner
        import ui.macos.banner
        import ui.macos.dashboard_window
        import ui.macos.menu_bar_app
        import ui.common
        import ui.app_launcher
        print("  ✓ All core/ and ui/ modules imported cleanly!")
    except Exception as e:
        print(f"  ❌ IMPORT ERROR: {e}")
        raise SystemExit(1)

    # Run automated test suite
    print("  🧪 Running automated unit test suite...")
    res = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=PROJECT_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  ❌ TEST SUITE FAILED:\n{res.stderr}\n{res.stdout}")
        raise SystemExit(1)
    print("  ✓ Test suite passed with 100% success!")
    print("✅ Python validation completed successfully (Zero Errors).\n")

def build_bundle():
    check_python_code()
    print(f"📦 Building macOS Native Bundle: {APP_DIR}...")
    if os.path.exists(APP_DIR):
        shutil.rmtree(APP_DIR)

    os.makedirs(MACOS_DIR, exist_ok=True)
    os.makedirs(RESOURCES_DIR, exist_ok=True)

    # 1. Copy AppIcon.icns
    icns_path = generate_icns()
    shutil.copy2(icns_path, os.path.join(RESOURCES_DIR, "AppIcon.icns"))

    # 2. Copy assets/
    assets_dest = os.path.join(RESOURCES_DIR, "assets")
    os.makedirs(assets_dest, exist_ok=True)
    assets_src = os.path.join(PROJECT_DIR, "assets")
    if os.path.exists(assets_src):
        for f_name in os.listdir(assets_src):
            s_path = os.path.join(assets_src, f_name)
            if os.path.isfile(s_path):
                shutil.copy2(s_path, os.path.join(assets_dest, f_name))

    # 3. Copy Python module directories (core/ and ui/) and main.py
    # Note: ui/linux (Qt runtime) is explicitly excluded from macOS bundle for clean packaging
    shutil.copytree(
        os.path.join(PROJECT_DIR, "core"),
        os.path.join(RESOURCES_DIR, "core"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        dirs_exist_ok=True
    )
    shutil.copytree(
        os.path.join(PROJECT_DIR, "ui"),
        os.path.join(RESOURCES_DIR, "ui"),
        ignore=shutil.ignore_patterns("linux", "__pycache__", "*.pyc"),
        dirs_exist_ok=True
    )
    shutil.copy2(os.path.join(PROJECT_DIR, "main.py"), os.path.join(RESOURCES_DIR, "main.py"))

    # Resolve dynamic version
    raw_ver = os.environ.get("RELEASE_TAG") or os.environ.get("VERSION") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not raw_ver:
        from core.domain.models import __version__
        raw_ver = __version__
    app_version = raw_ver.lstrip("v")

    with open(os.path.join(RESOURCES_DIR, "VERSION"), "w") as f:
        f.write(app_version)

    models_dest = os.path.join(RESOURCES_DIR, "core", "domain", "models.py")
    if os.path.exists(models_dest):
        with open(models_dest, "r") as f:
            m_code = f.read()
        import re
        m_code = re.sub(r'__version__\s*=\s*["\'][^"\']+["\']', f'__version__ = "{app_version}"', m_code)
        with open(models_dest, "w") as f:
            f.write(m_code)
    info_plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>FlightDeck</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.flightdeck.app</string>
    <key>CFBundleName</key>
    <string>FlightDeck</string>
    <key>CFBundleDisplayName</key>
    <string>FlightDeck</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{app_version}</string>
    <key>CFBundleVersion</key>
    <string>{app_version}</string>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleLocalizations</key>
    <array>
        <string>en</string>
        <string>it</string>
    </array>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSCalendarsUsageDescription</key>
    <string>FlightDeck requires Calendar access to display smart reminders and travel routes for your scheduled events.</string>
    <key>NSCalendarsFullAccessUsageDescription</key>
    <string>FlightDeck requires full Calendar access to fetch your upcoming meetings and travel routes.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
"""
    with open(os.path.join(CONTENTS_DIR, "Info.plist"), "w", encoding="utf-8") as f:
        f.write(info_plist_content)

    # 4b. Create localization directories (.lproj) so macOS recognizes bilingual support
    os.makedirs(os.path.join(RESOURCES_DIR, "en.lproj"), exist_ok=True)
    os.makedirs(os.path.join(RESOURCES_DIR, "it.lproj"), exist_ok=True)

    # 5. Create Launcher Bash executable in MacOS/FlightDeck.sh (debug fallback only)
    launcher_content = """#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
LOG_DIR="$HOME/.flightdeck"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/flightdeck.log"
LAUNCHER_LOG="$LOG_DIR/launcher.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Launcher] FlightDeck launching from $DIR..." >> "$LAUNCHER_LOG"

export PATH="/opt/miniconda3/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

PYTHON_BIN=""
for p in "/opt/miniconda3/bin/python3" "/usr/local/bin/python3" "/opt/homebrew/bin/python3" "$(which python3)"; do
    if [ -n "$p" ] && [ -x "$p" ] && "$p" -c "import AppKit" 2>/dev/null; then
        PYTHON_BIN="$p"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Launcher] Found Python with PyObjC: $PYTHON_BIN" >> "$LAUNCHER_LOG"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    ERR_MSG="Python 3 with PyObjC (AppKit) not found. Please install pyobjc: pip3 install pyobjc"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Launcher Error] $ERR_MSG" >> "$LAUNCHER_LOG"
    osascript -e "display alert \"FlightDeck Launch Error\" message \"$ERR_MSG\" as critical"
    exit 1
fi

BUNDLE_PYTHON="$DIR/../MacOS/FlightDeck_Python"
if [ ! -f "$BUNDLE_PYTHON" ]; then
    cp "$PYTHON_BIN" "$BUNDLE_PYTHON"
    chmod +x "$BUNDLE_PYTHON"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Launcher] Executing $BUNDLE_PYTHON $DIR/main.py --dashboard $@" >> "$LAUNCHER_LOG"
exec "$BUNDLE_PYTHON" "$DIR/main.py" --dashboard "$@" >> "$LOG_FILE" 2>&1
"""
    bash_path = os.path.join(MACOS_DIR, "FlightDeck.sh")
    with open(bash_path, "w", encoding="utf-8") as f:
        f.write(launcher_content)
    os.chmod(bash_path, 0o755)

    # 5b. Copy Python binary at build time so the C stub can exec it directly
    python_bin = None
    candidates = [sys.executable, "/opt/miniconda3/bin/python3", "/opt/homebrew/bin/python3", "/usr/local/bin/python3"]
    for p in candidates:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            try:
                result = subprocess.run([p, "-c", "import AppKit; print('ok')"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and "ok" in result.stdout:
                    python_bin = p
                    break
            except Exception:
                continue

    if python_bin:
        bundle_python_path = os.path.join(MACOS_DIR, "FlightDeck_Python")
        shutil.copy2(python_bin, bundle_python_path)
        os.chmod(bundle_python_path, 0o755)
        print(f"  ✓ Bundled Python binary: {python_bin} → FlightDeck_Python")
    else:
        print("  ⚠️ Could not find Python with PyObjC at build time; will fall back to shell launcher.")

    # 5c. Compile a Mach-O C stub that embeds Python IN-PROCESS via dlopen/Py_Main.
    # This is critical: execv replaces the process image, causing macOS to lose
    # the bundle association and refuse to show the app's menu bar. By running
    # Python in the same process, the Mach-O binary stays the running executable
    # and macOS fully recognises it as the bundle's app.
    c_stub = r"""
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include <string.h>
#include <sys/stat.h>
#include <dlfcn.h>
#include <mach-o/dyld.h>

/* Py_Main signature: int Py_Main(int argc, wchar_t **argv) */
typedef int (*Py_Main_t)(int, wchar_t **);
typedef wchar_t* (*Py_DecodeLocale_t)(const char *, size_t *);
typedef void (*Py_SetProgramName_t)(const wchar_t *);
typedef void (*Py_SetPath_t)(const wchar_t *);

int main(int argc, char **argv) {
    char exe_path[PATH_MAX];
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        fprintf(stderr, "FlightDeck: _NSGetExecutablePath failed\n");
        return 1;
    }

    char real_path[PATH_MAX];
    if (!realpath(exe_path, real_path)) {
        fprintf(stderr, "FlightDeck: realpath failed\n");
        return 1;
    }

    /* Trim to MacOS/ directory */
    char *last_slash = strrchr(real_path, '/');
    if (!last_slash) return 1;
    *last_slash = 0;

    char resources_path[PATH_MAX];
    char main_py_path[PATH_MAX];

    snprintf(resources_path, sizeof(resources_path), "%s/../Resources", real_path);
    snprintf(main_py_path, sizeof(main_py_path), "%s/../Resources/main.py", real_path);

    /* Redirect stdout/stderr to the log file */
    const char *home = getenv("HOME");
    if (home) {
        char log_dir[PATH_MAX];
        snprintf(log_dir, sizeof(log_dir), "%s/.flightdeck", home);
        mkdir(log_dir, 0755);
        char log_path[PATH_MAX];
        snprintf(log_path, sizeof(log_path), "%s/flightdeck.log", log_dir);
        FILE *log_fp = fopen(log_path, "a");
        if (log_fp) {
            dup2(fileno(log_fp), STDOUT_FILENO);
            dup2(fileno(log_fp), STDERR_FILENO);
            fclose(log_fp);
        }
    }

    /* Set PYTHONPATH to Resources/ so our modules are importable */
    setenv("PYTHONPATH", resources_path, 1);

    /* Try to find libpython - check common locations */
    void *python_lib = NULL;
    const char *dylib_candidates[] = {
        "PLACEHOLDER_DYLIB",
        "/opt/miniconda3/lib/libpython3.13.dylib",
        "/opt/homebrew/lib/libpython3.13.dylib",
        "/usr/local/lib/libpython3.13.dylib",
        "/opt/miniconda3/lib/libpython3.12.dylib",
        "/opt/homebrew/lib/libpython3.12.dylib",
        "/usr/local/lib/libpython3.12.dylib",
        NULL
    };

    for (int i = 0; dylib_candidates[i] != NULL; i++) {
        python_lib = dlopen(dylib_candidates[i], RTLD_LAZY | RTLD_GLOBAL);
        if (python_lib) {
            fprintf(stderr, "[FlightDeck Launcher] Loaded: %s\n", dylib_candidates[i]);
            break;
        }
    }

    if (!python_lib) {
        fprintf(stderr, "FlightDeck: Could not load libpython. dlerror: %s\n", dlerror());
        /* Fall back to execv as last resort */
        char python_bin[PATH_MAX];
        snprintf(python_bin, sizeof(python_bin), "%s/FlightDeck_Python", real_path);
        char *fallback_argv[] = {python_bin, main_py_path, NULL};
        execv(python_bin, fallback_argv);
        perror("FlightDeck: execv fallback also failed");
        return 1;
    }

    /* Resolve Py_Main and helpers */
    Py_Main_t py_main = (Py_Main_t)dlsym(python_lib, "Py_Main");
    Py_DecodeLocale_t py_decode = (Py_DecodeLocale_t)dlsym(python_lib, "Py_DecodeLocale");

    if (!py_main || !py_decode) {
        fprintf(stderr, "FlightDeck: Could not resolve Py_Main/Py_DecodeLocale\n");
        return 1;
    }

    /* Build wchar_t argv for Py_Main: [exe_path, main.py, original_args...] */
    int py_argc = argc + 1;  /* insert main.py as argv[1] */
    wchar_t **py_argv = malloc(sizeof(wchar_t *) * (py_argc + 1));
    if (!py_argv) return 1;

    py_argv[0] = py_decode(exe_path, NULL);       /* argv[0] = our Mach-O binary */
    py_argv[1] = py_decode(main_py_path, NULL);    /* argv[1] = main.py */
    for (int i = 1; i < argc; i++) {
        py_argv[i + 1] = py_decode(argv[i], NULL);
    }
    py_argv[py_argc] = NULL;

    /* Run Python — this blocks until the app exits */
    int rc = py_main(py_argc, py_argv);
    return rc;
}
"""
    # Find the actual dylib path to embed in the C code
    dylib_path = None
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    for candidate in [
        os.path.join(sys.prefix, "lib", f"libpython{py_version}.dylib"),
        f"/opt/miniconda3/lib/libpython{py_version}.dylib",
        f"/opt/homebrew/lib/libpython{py_version}.dylib",
        f"/usr/local/lib/libpython{py_version}.dylib",
    ]:
        if os.path.exists(candidate):
            dylib_path = candidate
            break

    if dylib_path:
        c_stub = c_stub.replace("PLACEHOLDER_DYLIB", dylib_path)
        print(f"  ✓ Found libpython dylib: {dylib_path}")
    else:
        c_stub = c_stub.replace("PLACEHOLDER_DYLIB", f"/opt/miniconda3/lib/libpython{py_version}.dylib")
        print("  ⚠️ libpython dylib not found at expected paths, using default")

    c_path = os.path.join(PROJECT_DIR, "launcher_stub.c")
    with open(c_path, "w") as f:
        f.write(c_stub)

    launcher_path = os.path.join(MACOS_DIR, "FlightDeck")
    # Compile with include path for Python.h (not strictly needed for dlopen approach,
    # but ensures the build environment is clean)
    subprocess.run(["clang", "-O2", "-Wall", c_path, "-o", launcher_path], check=True)
    os.remove(c_path)

    # 5d. Remove quarantine extended attributes and apply ad-hoc codesign with designated requirement
    try:
        subprocess.run(["xattr", "-cr", APP_DIR], check=False)
        subprocess.run([
            "codesign", "--force", "--deep", "-s", "-",
            "-i", "com.flightdeck.app",
            "-r", '=designated => identifier "com.flightdeck.app"',
            APP_DIR
        ], check=False)
        print(f"  ✓ Applied ad-hoc codesign signature with designated requirement (id: com.flightdeck.app) to {APP_NAME}")
    except Exception as cs_err:
        print(f"  Note on codesign: {cs_err}")

    print(f"🚀 FlightDeck.app successfully created in: {APP_DIR}")

    # 6. Install cleanly into /Applications
    apps_target = "/Applications/FlightDeck.app"
    try:
        if os.path.exists(apps_target):
            if os.path.islink(apps_target):
                os.unlink(apps_target)
            else:
                shutil.rmtree(apps_target)
        shutil.copytree(APP_DIR, apps_target, symlinks=True)
        print(f"📦 Installed cleanly into /Applications: {apps_target}")
    except Exception as e:
        print(f"Applications install note: {e}")

    # 7. Create Desktop shortcut
    desktop_app = os.path.expanduser("~/Desktop/FlightDeck.app")
    try:
        if os.path.exists(desktop_app):
            if os.path.islink(desktop_app):
                os.unlink(desktop_app)
            else:
                shutil.rmtree(desktop_app)
        os.symlink(apps_target if os.path.exists(apps_target) else APP_DIR, desktop_app)
        print(f"📍 Shortcut created on Desktop: {desktop_app}")
    except Exception as e:
        print(f"Desktop note: {e}")

if __name__ == "__main__":
    build_bundle()
