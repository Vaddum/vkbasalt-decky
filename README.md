# vkBasalt Manager — Decky Loader Plugin

**Graphical interface for managing vkBasalt on Steam Deck, built into the Quick Access Menu**

vkBasalt Manager brings the same installation, configuration, and shader management for Vulkan post-processing effects as the original [vkbasalt-manager](https://github.com/Vaddum/vkbasalt-manager) script — but as a native Decky Loader plugin, usable in Gaming Mode without ever leaving the Quick Access Menu.

## Quick Installation

Requires [Decky Loader](https://decky.xyz/) to already be installed.

1. Download the plugin ZIP (see [Building](#building) if you're compiling it yourself)
2. Open the Quick Access Menu → **Settings** → **Developer** → **Install Plugin from ZIP File**
3. Select the ZIP
4. Open the Quick Access Menu, find **vkBasalt Manager**, and install vkBasalt from there

## Key Features

- **Auto Install**: One-click installation of vkBasalt + ReShade shaders, directly from Gaming Mode
- **Shader Manager**: Enable/disable effects with toggles in the Quick Access Menu
- **Live Parameter Sliders**: Adjust effect parameters without editing config files
- **Toggle Key**: Customizable in-game hotkey
- **Per-Game Activation**: Copy `ENABLE_VKBASALT=1 %command%` straight to clipboard for a game's launch options

### vkBasalt Built-in Effects 🔵

#### CAS
- **Sharpness** (0.0-1.0, default: 0.4): Sharpening intensity

#### FXAA
- **Subpix Quality** (0.0-1.0, default: 0.75): Subpixel antialiasing
- **Edge Threshold** (0.063-0.333, default: 0.125): Edge detection sensitivity

#### SMAA
- **Edge Detection** (luma/color/depth, default: luma): Detection method
- **Threshold** (0.01-0.20, default: 0.05): Sensitivity
- **Max Steps** (8-64, default: 32): Quality vs performance

#### DLS
- **Sharpening** (0.0-1.0, default: 0.5): Sharpening strength
- **Denoise** (0.0-1.0, default: 0.17): Noise reduction

### Supported External Effects (ReShade)

#### Light Effects 🟢
- **Border**: Adds customizable borders to fix edges
- **Curves**: S-curve contrast without clipping
- **Daltonize**: Color blindness correction filter
- **Defring**: Removes chromatic aberration/fringing
- **Levels**: Adjusts black/white point range
- **LiftGammaGain**: Professional shadows/midtones/highlights tool
- **Monochrome**: Black & white conversion with film presets
- **Sepia**: Vintage sepia tone effect
- **Technicolor**: Classic vibrant film process look
- **Tonemap**: Comprehensive tone mapping controls
- **Vibrance**: Smart saturation enhancement tool

#### Medium Effects 🟠
- **AdaptiveSharpen**: Smart edge-aware sharpening with minimal artifacts
- **Cartoon**: Creates cartoon-like edge enhancement
- **DPX**: Film-style color grading effect
- **FilmGrain**: Adds realistic film grain noise
- **LumaSharpen**: Luminance-based detail enhancement
- **Nostalgia**: Retro gaming visual style emulation
- **SuperEagle**: Diagonal smoothing for pixel art, keeps text sharp
- **Vignette**: Darkened edges camera lens effect

#### Heavy Effects 🔴
- **4xBRZ**: Complex pixel art upscaling for retro games
- **Clarity**: Advanced sharpening with blur masking
- **CRT**: Simulates old CRT monitor appearance
- **FakeHDR**: Simulates HDR with bloom effects
- **SmartSharp**: Depth-aware intelligent sharpening

## Usage

### Quick Access Menu

- **Built-in Effects**: Toggle CAS/FXAA/SMAA/DLS, sliders appear when an effect is enabled
- **External Shaders**: Toggle any `.fx` shader found in `~/.config/reshade/Shaders`
- **Settings**: Toggle key, copy launch option, uninstall

### In-Game Controls

**Toggle Effects**: Press the configured key (default: Home)

Effects activate in real-time, no restart required.

## File Locations

- **Configuration**: `~/.config/vkBasalt/vkBasalt.conf`
- **Shaders**: `~/.config/reshade/Shaders/`
- **Libraries**: `~/.local/lib/libvkbasalt.so` and `~/.local/lib32/libvkbasalt.so`
- **Plugin**: `~/homebrew/plugins/vkbasalt-manager/`

## Building

This plugin is built on the official [decky-plugin-template](https://github.com/SteamDeckHomebrew/decky-plugin-template).

1. Use the template to create your own repo (or clone it), then copy `main.py`, `plugin.json`, and `src/index.tsx` into it, overwriting the template's versions.
2. Install dependencies and build:
   ```bash
   pnpm i
   pnpm run build
   ```
3. Package it for installation:
   ```bash
   mkdir -p /tmp/vkbasalt-manager/dist
   cp dist/index.js /tmp/vkbasalt-manager/dist/
   cp plugin.json package.json main.py /tmp/vkbasalt-manager/
   cd /tmp && zip -r vkbasalt-manager.zip vkbasalt-manager
   ```

If Node.js/pnpm aren't available on your Deck:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
source ~/.bashrc
nvm install --lts
corepack enable
corepack prepare pnpm@latest --activate
```

## Troubleshooting

**No effects visible**: Check that the game uses the Vulkan renderer and that `ENABLE_VKBASALT=1 %command%` is set in its launch options

**Installation fails / "Could not reach the AUR mirror"**: Verify your internet connection; the Chaotic-AUR mirror may also be temporarily unavailable

**Performance drops**: Disable heavy effects (🔴)

**Toggle key not working**: Change the key in the plugin's Settings section

**`OPENSSL_x.x.x not found` in the plugin's logs**: Caused by Decky's PyInstaller-bundled backend leaking `LD_LIBRARY_PATH` into subprocess calls; the plugin strips it before calling `curl`/`wget`/`tar`

## About

Decky Loader plugin port of [vkbasalt-manager](https://github.com/Vaddum/vkbasalt-manager), a GUI for managing vkBasalt on Steam Deck.
