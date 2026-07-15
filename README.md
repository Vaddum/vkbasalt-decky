# vkBasalt Manager — Decky Loader Plugin

Manage [vkBasalt](https://github.com/DadSchoorse/vkBasalt) directly from the Quick Access Menu on Steam Deck: install it, toggle its post-processing effects, and adjust their parameters — no terminal required.

## Features

- One-click install/uninstall of vkBasalt (64 and 32-bit) from the Chaotic-AUR mirror
- Toggle built-in effects: **CAS**, **FXAA**, **SMAA**, **DLS**, with adjustable sliders (sharpness, thresholds, denoise...)
- Toggle any external ReShade `.fx` shader dropped into `~/.config/reshade/Shaders`
- Configurable toggle key (default: `Home`)
- Per-game activation: copy `ENABLE_VKBASALT=1 %command%` straight to clipboard for pasting into a game's launch options

## Requirements

- [Decky Loader](https://decky.xyz/) installed on your Steam Deck
- Internet connection (to fetch vkBasalt and the bundled ReShade shaders)
- `wget`, `curl`, `tar`, `unzip` (present by default on SteamOS)
- [Node.js](https://nodejs.org/) + [pnpm](https://pnpm.io/) to build the plugin (see below)

## Building

This plugin is built on top of the official [decky-plugin-template](https://github.com/SteamDeckHomebrew/decky-plugin-template).

1. Use the template to create your own repo (or clone it directly), then copy this plugin's `main.py`, `plugin.json`, and `src/index.tsx` into it, overwriting the template's versions.
2. Install dependencies and build:
   ```bash
   pnpm i
   pnpm run build
   ```
   This produces `dist/index.js`.

If `pnpm`/Node.js aren't available on your Deck and you'd rather build there than on a separate machine, install them without touching the read-only system partition:
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
source ~/.bashrc
nvm install --lts
corepack enable
corepack prepare pnpm@latest --activate
```

## Installing on the Deck

Build a clean install package (don't just zip the whole dev folder — it needs this exact structure):

```bash
rm -rf /tmp/vkbasalt-manager
mkdir -p /tmp/vkbasalt-manager/dist
cp dist/index.js /tmp/vkbasalt-manager/dist/
cp plugin.json package.json main.py /tmp/vkbasalt-manager/
cd /tmp && zip -r vkbasalt-manager.zip vkbasalt-manager
```

Then in Gaming Mode: Quick Access Menu → **Settings** → **Developer** → **Install Plugin from ZIP File** → select `vkbasalt-manager.zip`.

Alternatively, copy `plugin.json`, `package.json`, `main.py`, and `dist/index.js` directly into `~/homebrew/plugins/vkbasalt-manager/` on the Deck and restart the plugin loader:
```bash
sudo systemctl restart plugin_loader
```

## Usage

1. Open the plugin from the Quick Access Menu and install vkBasalt.
2. Enable the effects you want and adjust their sliders if needed.
3. Tap **Copy `ENABLE_VKBASALT=1 %command%`** and paste it into the target game's **Launch Options** (Steam → game Properties → General).
4. Launch the game. Press the toggle key (`Home` by default) in-game to enable/disable effects on the fly.
5. Use **Uninstall vkBasalt** from the plugin to remove everything (libraries, Vulkan layer registration, config) without touching your games or Steam settings.

## Troubleshooting

- **"Could not reach the AUR mirror" / empty response** — check your internet connection; the Chaotic-AUR mirror may also be temporarily unavailable. The plugin sends a browser-like User-Agent to avoid being blocked by anti-bot mirror rules.
- **`OPENSSL_x.x.x not found` errors in the plugin's log** — this comes from Decky's own PyInstaller-bundled backend leaking its `LD_LIBRARY_PATH` into subprocess calls. The plugin strips it before calling `curl`/`wget`/`tar`, so this shouldn't occur; if it does on your setup, check `~/homebrew/logs/vkbasalt-manager/` for the exact error.
- **A custom ReShade shader causes a black screen** — check vkBasalt's own logs by adding `VKBASALT_LOG_LEVEL=trace %command% > ~/vkbasalt.log 2>&1` as a launch option, then inspect `~/vkbasalt.log` for compiler errors. Not all ReShade FX syntax is supported by vkBasalt's bundled shader compiler.

## Credits

- [vkBasalt](https://github.com/DadSchoorse/vkBasalt) by DadSchoorse
- [ReShade](https://reshade.me/) and its shader ecosystem
- [Decky Loader](https://decky.xyz/), `@decky/ui`, and `@decky/api`
- Ported from the original [vkbasalt_manager.sh](https://github.com/Vaddum/vkbasalt-manager) script

## License

MIT (adjust to match your repo's actual license).
