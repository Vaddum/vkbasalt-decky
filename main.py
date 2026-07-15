"""
vkBasalt Manager - Decky Loader plugin backend
Ported from the vkbasalt_manager.sh script (Vaddum/vkbasalt-manager).

Design notes vs. the original bash script:
- No zenity: the UI is entirely handled by the React frontend (src/index.tsx).
- No "sudo pacman -S zenity/wget/unzip/tar": the Decky backend already runs
  with the right permissions on the deck account, and these tools are present
  by default on SteamOS. If one is missing, a clear error is returned instead
  of silently installing it.
- Profiles / diagnostics / import-export are not included here (better suited
  to a desktop UI than the Quick Access Menu). The natural extension point is
  _write_config() / _read_config_dict() if you want to add them back.
- Per-external-shader parameter editing (reading/writing uniform sliders in
  .fx files) was tried and then dropped: too much complexity for too little
  practical benefit. Users who want to tweak an external shader's defaults
  can still edit the .fx file directly.
"""

import os
import re
import shutil
import subprocess
import tempfile

import decky

HOME = os.environ.get("HOME", os.path.expanduser("~"))
CONFIG_FILE = f"{HOME}/.config/vkBasalt/vkBasalt.conf"
SHADER_PATH = f"{HOME}/.config/reshade/Shaders"
TEXTURE_PATH = f"{HOME}/.config/reshade/Textures"
AUR_BASE = "https://builds.garudalinux.org/repos/chaotic-aur/x86_64/"
REPO_ZIP = "https://github.com/Vaddum/vkbasalt-manager/archive/refs/heads/main.zip"

LAYER_FILES = [
    f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.json",
    f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.x86.json",
]
# GLOBAL_VAR: SteamOS permanently sets this environment variable on the Deck,
# so the layer loads for every Vulkan process without a launch option.
# PERGAME_VAR: standard vkBasalt behaviour, requires adding
# "ENABLE_VKBASALT=1 %command%" to a game's launch options to enable it.
GLOBAL_VAR = "SteamDeck"
PERGAME_VAR = "ENABLE_VKBASALT"

BUILTIN_EFFECTS = ["cas", "fxaa", "smaa", "dls"]

# id -> (display name, category, description)
SHADER_INFO = {
    "cas": ("CAS", "blue", "AMD Adaptive Sharpening - enhances detail without artifacts (built-in)"),
    "fxaa": ("FXAA", "blue", "Fast anti-aliasing, smooths jagged edges quickly (built-in)"),
    "smaa": ("SMAA", "blue", "High quality anti-aliasing, better than FXAA (built-in)"),
    "dls": ("DLS", "blue", "Denoised Luma Sharpening - smart sharpening without noise (built-in)"),
    "4xbrz": ("4xBRZ", "red", "Complex pixel art upscaling for retro games"),
    "adaptivesharpen": ("AdaptiveSharpen", "orange", "Smart edge-aware sharpening with minimal artifacts"),
    "border": ("Border", "green", "Customizable borders to fix image edges"),
    "cartoon": ("Cartoon", "orange", "Cartoon-like edge enhancement"),
    "clarity": ("Clarity", "red", "Advanced sharpening with blur masking"),
    "crt": ("CRT", "red", "Simulates an old CRT monitor"),
    "curves": ("Curves", "green", "S-curve contrast without clipping"),
    "daltonize": ("Daltonize", "green", "Color blindness correction filter"),
    "defring": ("Defring", "green", "Removes chromatic aberration"),
    "dpx": ("DPX", "orange", "Film-style color grading"),
    "fakehdr": ("FakeHDR", "red", "Simulates HDR with bloom"),
    "filmgrain": ("FilmGrain", "orange", "Adds realistic film grain"),
    "levels": ("Levels", "green", "Adjusts black/white points"),
    "liftgammagain": ("LiftGammaGain", "green", "Pro shadows/midtones/highlights tool"),
    "lumasharpen": ("LumaSharpen", "orange", "Luminance-based detail enhancement"),
    "monochrome": ("Monochrome", "green", "Black & white conversion with film presets"),
    "nostalgia": ("Nostalgia", "orange", "Retro gaming visual style"),
    "sepia": ("Sepia", "green", "Vintage sepia effect"),
    "smartsharp": ("SmartSharp", "red", "Depth-aware smart sharpening"),
    "supereagle": ("SuperEagle", "orange", "Diagonal smoothing for pixel art, keeps text sharp"),
    "technicolor": ("Technicolor", "green", "Classic vibrant film look"),
    "tonemap": ("Tonemap", "green", "Full tone mapping controls"),
    "vibrance": ("Vibrance", "green", "Smart saturation boost"),
    "vignette": ("Vignette", "orange", "Darkened edges, camera lens effect"),
}

PARAM_DEFAULTS = {
    "cas": {"casSharpness": "0.4"},
    "fxaa": {"fxaaQualitySubpix": "0.75", "fxaaQualityEdgeThreshold": "0.125"},
    "smaa": {"smaaEdgeDetection": "luma", "smaaThreshold": "0.05", "smaaMaxSearchSteps": "32"},
    "dls": {"dlsSharpness": "0.5", "dlsDenoise": "0.17"},
}


def _clean_env():
    # The Decky backend runs as a PyInstaller-frozen executable, which sets
    # LD_LIBRARY_PATH to point to its own bundled libraries (including an older
    # libssl.so.3). System binaries like curl/wget/tar then try to load that
    # bundled libssl instead of the system one, causing version mismatches
    # (e.g. "version `OPENSSL_3.2.0' not found"). Stripping LD_LIBRARY_PATH for
    # subprocess calls makes them use the system's own libraries again.
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    return env


def _run(cmd, **kwargs):
    kwargs.setdefault("env", _clean_env())
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


class Plugin:
    # ---------------------------------------------------------------- status
    async def get_status(self):
        lib64 = os.path.isfile(f"{HOME}/.local/lib/libvkbasalt.so")
        lib32 = os.path.isfile(f"{HOME}/.local/lib32/libvkbasalt.so")
        shaders = os.path.isdir(SHADER_PATH) and len(os.listdir(SHADER_PATH)) > 0
        if lib64 and lib32 and shaders:
            return {"state": "installed"}
        if lib64 and lib32:
            return {"state": "partial"}
        return {"state": "missing"}

    # --------------------------------------------------------------- install
    async def install(self):
        try:
            for d in (
                f"{HOME}/.local/lib",
                f"{HOME}/.local/lib32",
                f"{HOME}/.local/share/vulkan/implicit_layer.d",
                f"{HOME}/.config/vkBasalt",
                f"{HOME}/.config/reshade",
            ):
                os.makedirs(d, exist_ok=True)

            for tool in ("wget", "tar", "curl", "unzip"):
                if shutil.which(tool) is None:
                    return {
                        "ok": False,
                        "error": f"Missing tool: {tool}. Install it once from a Desktop Mode "
                                 f"terminal (sudo pacman -S {tool}), then retry the installation.",
                    }

            listing_proc = _run(["curl", "-s", "-A", "Mozilla/5.0 (X11; Linux x86_64) vkbasalt-manager-decky", AUR_BASE])
            listing = listing_proc.stdout
            if not listing:
                decky.logger.error(
                    f"curl on AUR_BASE returned nothing (exit code {listing_proc.returncode}, "
                    f"stderr: {listing_proc.stderr.strip()})"
                )
                return {
                    "ok": False,
                    "error": "Could not reach the AUR mirror (empty response). Check your internet "
                             "connection and try again in a moment.",
                }
            match = re.search(r"vkbasalt-[0-9.\-]*-x86_64", listing)
            if not match:
                decky.logger.error(f"AUR mirror listing did not match expected pattern. First 300 chars: {listing[:300]!r}")
                return {
                    "ok": False,
                    "error": "vkBasalt package not found in the AUR mirror listing (the mirror page "
                             "format may have changed, or it's temporarily unavailable).",
                }
            pkg = f"{match.group(0)}.pkg.tar.zst"
            lib32_pkg = f"lib32-{pkg}"

            with tempfile.TemporaryDirectory() as tmp:
                pkg_file = os.path.join(tmp, "vkbasalt.tar.zst")
                lib32_file = os.path.join(tmp, "vkbasalt32.tar.zst")

                if _run(["wget", "-q", "--user-agent=Mozilla/5.0", f"{AUR_BASE}{pkg}", "-O", pkg_file]).returncode != 0:
                    return {"ok": False, "error": "Download failed (64-bit package)."}
                if _run(["wget", "-q", "--user-agent=Mozilla/5.0", f"{AUR_BASE}{lib32_pkg}", "-O", lib32_file]).returncode != 0:
                    return {"ok": False, "error": "Download failed (32-bit package)."}

                if _run(["tar", "-tf", pkg_file]).returncode != 0 or _run(["tar", "-tf", lib32_file]).returncode != 0:
                    return {"ok": False, "error": "Downloaded package appears to be corrupted."}

                _run(["tar", "xf", pkg_file, "--strip-components=2",
                      "--directory", f"{HOME}/.local/lib/", "usr/lib/libvkbasalt.so"])
                _run(["tar", "xf", lib32_file, "--strip-components=2",
                      "--directory", f"{HOME}/.local/lib32/", "usr/lib32/libvkbasalt.so"])

                jobs = (
                    (pkg_file, "usr/share/vulkan/implicit_layer.d/vkBasalt.json",
                     f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.json",
                     f"{HOME}/.local/lib/libvkbasalt.so"),
                    (lib32_file, "usr/share/vulkan/implicit_layer.d/vkBasalt.x86.json",
                     f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.x86.json",
                     f"{HOME}/.local/lib32/libvkbasalt.so"),
                )
                for src_pkg, inner_path, dst, libpath in jobs:
                    extract = _run(["tar", "xf", src_pkg, "--to-stdout", inner_path])
                    if extract.returncode != 0:
                        return {"ok": False, "error": f"Could not extract: {inner_path}"}
                    # Default mode: "per game" (standard vkBasalt behaviour). Add
                    # ENABLE_VKBASALT=1 %command% to a game's launch options to enable it.
                    content = extract.stdout.replace("libvkbasalt.so", libpath)
                    with open(dst, "w") as fh:
                        fh.write(content)

                # ReShade shaders + textures bundled in the manager's repo
                zip_path = os.path.join(tmp, "shaders.zip")
                if _run(["wget", "-q", "--user-agent=Mozilla/5.0", REPO_ZIP, "-O", zip_path]).returncode == 0:
                    _run(["unzip", "-q", "-o", zip_path, "-d", tmp])
                    src_dir = os.path.join(tmp, "vkbasalt-manager-main", "reshade")
                    if os.path.isdir(src_dir):
                        shutil.copytree(src_dir, f"{HOME}/.config/reshade", dirs_exist_ok=True)

            if not os.path.isfile(CONFIG_FILE):
                self._write_config(["cas"])

            decky.logger.info("vkBasalt installed successfully")
            return {"ok": True}
        except Exception as e:
            decky.logger.error(f"install() error: {e}")
            return {"ok": False, "error": str(e)}

    async def uninstall(self):
        try:
            shutil.rmtree(f"{HOME}/.config/vkBasalt", ignore_errors=True)
            shutil.rmtree(f"{HOME}/.config/reshade", ignore_errors=True)
            for p in (
                f"{HOME}/.local/lib/libvkbasalt.so",
                f"{HOME}/.local/lib32/libvkbasalt.so",
                f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.json",
                f"{HOME}/.local/share/vulkan/implicit_layer.d/vkBasalt.x86.json",
            ):
                if os.path.isfile(p):
                    os.remove(p)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------------------------------------------------------- shaders
    async def get_shaders(self):
        active = self._read_active_effects()
        shaders = []

        for key in BUILTIN_EFFECTS:
            name, category, desc = SHADER_INFO.get(key, (key, "grey", ""))
            shaders.append({"id": key, "name": name, "category": category,
                             "description": desc, "enabled": key in active, "builtin": True})

        if os.path.isdir(SHADER_PATH):
            for f in sorted(os.listdir(SHADER_PATH)):
                if not f.endswith(".fx"):
                    continue
                key = f[:-3]
                lower = key.lower()
                if lower in BUILTIN_EFFECTS:
                    continue
                name, category, desc = SHADER_INFO.get(lower, (key, "grey", "Available graphics effect"))
                shaders.append({"id": lower, "name": name, "category": category,
                                 "description": desc, "enabled": lower in active, "builtin": False})
        return shaders

    async def set_shader_enabled(self, shader_id: str, enabled: bool):
        active = self._read_active_effects()
        shader_id = shader_id.lower()
        if enabled and shader_id not in active:
            active.append(shader_id)
        elif not enabled and shader_id in active:
            active.remove(shader_id)
        self._write_config(active)
        return {"ok": True, "effects": active}

    # ------------------------------------------------------------- settings
    async def get_params(self, shader_id: str):
        defaults = PARAM_DEFAULTS.get(shader_id, {})
        current = self._read_config_dict()
        return {k: current.get(k, v) for k, v in defaults.items()}

    async def set_param(self, key: str, value: str):
        self._patch_config_line(key, value)
        return {"ok": True}

    async def get_toggle_key(self):
        return self._read_config_dict().get("toggleKey", "Home")

    async def set_toggle_key(self, key: str):
        self._patch_config_line("toggleKey", key)
        return {"ok": True}

    # ---------------------------------------------------------------- helpers
    def _read_config_dict(self):
        values = {}
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE) as fh:
                for line in fh:
                    if "=" in line and not line.strip().startswith("#"):
                        k, _, v = line.partition("=")
                        values[k.strip()] = v.strip()
        return values

    def _read_active_effects(self):
        raw = self._read_config_dict().get("effects", "")
        return [e for e in raw.split(":") if e]

    def _write_config(self, effects: list):
        current = self._read_config_dict()
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        lines = [
            f"effects = {':'.join(effects)}",
            f"reshadeTexturePath = {TEXTURE_PATH}",
            f"reshadeIncludePath = {SHADER_PATH}",
            "depthCapture = off",
            "enableOnLaunch = True",
            f"toggleKey = {current.get('toggleKey', 'Home')}",
        ]
        for shader in effects:
            if shader in PARAM_DEFAULTS:
                for k, default in PARAM_DEFAULTS[shader].items():
                    lines.append(f"{k} = {current.get(k, default)}")
            else:
                for name_var in (shader, shader.capitalize(), shader.upper()):
                    path = f"{SHADER_PATH}/{name_var}.fx"
                    if os.path.isfile(path):
                        lines.append(f"{shader} = {path}")
                        break
        with open(CONFIG_FILE, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def _patch_config_line(self, key: str, value: str):
        current = self._read_config_dict()
        current[key] = value
        effects = self._read_active_effects()
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        lines = [f"effects = {':'.join(effects)}"]
        for k, v in current.items():
            if k == "effects":
                continue
            lines.append(f"{k} = {v}")
        with open(CONFIG_FILE, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    # -------------------------------------------------------------- lifecycle
    async def _main(self):
        self._ensure_pergame_activation()
        decky.logger.info("vkBasalt Manager plugin loaded")

    def _ensure_pergame_activation(self):
        # Silently reverts to "per game" activation any install that would have
        # been configured in global mode by an earlier version of the plugin/script.
        try:
            for p in LAYER_FILES:
                if not os.path.isfile(p):
                    continue
                with open(p, "r", errors="ignore") as fh:
                    content = fh.read()
                if GLOBAL_VAR in content:
                    content = content.replace(GLOBAL_VAR, PERGAME_VAR)
                    with open(p, "w") as fh:
                        fh.write(content)
                    decky.logger.info(f"{p} reverted to per-game activation")
        except OSError as e:
            decky.logger.error(f"_ensure_pergame_activation error: {e}")

    async def _unload(self):
        pass

    async def _uninstall(self):
        pass
