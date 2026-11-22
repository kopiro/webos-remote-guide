<img src="app/largeIcon.png" width="96" height="96" alt="Remote Guide icon">

# Remote Guide for webOS

Remote Guide is a companion app for Magic Mapper on LG webOS. See what each remapped button does and run its short-press action directly from the guide. Remote Guide puts your current Magic Mapper shortcuts beside a photograph of the European MR24 and draws an arrow to each physical key. Click a label or the pictured key to run it. With the D-pad, highlight a label and press OK. Moving the pointer or changing focus only highlights the key.

![Remote Guide showing sample HDMI, brightness and app shortcuts](docs/remote-guide.webp)

## How it works

When Magic Mapper loads its configuration, a Python helper writes button names, action descriptions and press details into the installed web app. Remote Guide reads that file when opened, when it returns to the foreground and every 15 seconds while visible. A click sends the selected key to Magic Mapper over an authenticated connection on the TV’s loopback interface. Magic Mapper resolves it against the loaded configuration and dispatches its actions while Remote Guide is in the foreground. Buttons outside the photographed layout still appear as text entries.

The physical button names and positions belong to the MR24 layout. Set the optional `title` attribute on an action in `magic_mapper_config.json` to choose exactly what the guide displays. For untitled actions, labels are generated from the configured function and arguments. The exporter supplies wording for known actions and apps, while optional local labels supply names for HDMI devices, scripts and webhooks.

## Build and install

You need the webOS CLI on your computer and a TV with Python 3, shell access and an existing Magic Mapper installation. The installer supports the file-based mapper that loads its JSON configuration into `button_map` in `get_button_map()`. It checks for that loader before applying its hook.

1. Package the web app from the repository root.

   ```sh
   mkdir -p dist
   ares-package app --no-minify -o dist
   ```

2. Install the resulting IPK using your usual webOS package installer. With a configured webOS CLI device named `my-tv`, use `ares-install -d my-tv dist/*.ipk`.
3. Copy the `mapper` directory to a temporary directory on the TV and run `python3 mapper/install.py` there with permission to update Magic Mapper. The installer saves a backup before editing its loader and generates the first set of labels immediately. Restart Magic Mapper using your existing launcher after installation or a configuration change. Run the installer and restart Magic Mapper again after reinstalling the IPK.
4. Open **Remote Guide** from the TV’s app list.

## Name a shortcut in Magic Mapper

A title belongs to the same action as its function and inputs. Moving that action to another key moves its title too.

```json
{
  "2": {
    "title": "Play on the game console",
    "function": "launch_app",
    "inputs": {"app_id": "com.webos.app.hdmi2"},
    "allow_long_press": true
  }
}
```

For a sequence, put a title on its main action to name the row. Multiple explicit titles appear in order. The detail line still describes each step, including untitled steps. A title is purely descriptive. Clicks run the configured short press and honor the mapper’s app scope and pass-through settings.

## Optional fallback labels

Optional JSON files beside the Python installer let you name HDMI inputs, scripts and webhooks. They stay local and are ignored by Git. For example, this `guide-labels.json` gives HDMI 2 a descriptive name.

```json
{
  "inputs": {"2": "Game console"}
}
```

The same file accepts a `device` string for the header and a `scripts` object mapping script paths to display names. A separate `webhook-labels.json` maps the SHA-256 digest of each complete webhook URL, encoded as UTF-8, to a display name. An unknown webhook gets a generic label. Restart Magic Mapper after editing labels on the TV. If you edit the local copies, rerun the installer and then restart Magic Mapper.

## Development

Run `python3 -m unittest discover -s tests` to check the mapping exporter.

The remote photograph is from [LG’s MR24GN product gallery](https://www.lg.com/pl/telewizory-i-soundbary/akcesoria/akb76045103/). The button mappings come from [Magic Mapper](https://github.com/andrewfraley/magic_mapper).
