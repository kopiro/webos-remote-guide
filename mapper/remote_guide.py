"""Publish the bindings Magic Mapper just loaded as display-only descriptions."""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from guide_control import APP_ID, active_actions

APP = Path("/media/developer/apps/usr/palm/applications/me.kopiro.remoteguide")
APPS = {"com.beb.plxnative": "PlxNative", "io.github.danzig666.ytnative": "YTnative"}


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[\w.!-]{1,96}", value)


def describe(action, webhooks, key, labels):
    name = action.get("function")
    data = action.get("inputs") or {}
    if name in ("curl", "post_ha_webhook"):
        digest = hashlib.sha256(str(data.get("url", "")).encode()).hexdigest()
        return webhooks.get(digest, "Call Home Assistant" if name == "post_ha_webhook" else "Send web request")
    if name == "launch_app":
        app = data.get("app_id")
        hdmi = re.fullmatch(r"com\.webos\.app\.hdmi([1-4])", app or "")
        if hdmi:
            port = hdmi[1]
            device = labels.get("inputs", {}).get(port)
            return "HDMI " + port + (" · " + device if device else "")
        return "Open " + APPS.get(app, app if identifier(app) else "app")
    if name == "run_script":
        return labels.get("scripts", {}).get(data.get("path"), "Run custom script")
    if name == "toggle_piccap":
        return "Toggle Ambilight"
    if name in ("increase_oled_light", "reduce_oled_light"):
        sign = "+" if name == "increase_oled_light" else "−"
        step = data.get("increment")
        return "OLED brightness " + (sign + str(step) if isinstance(step, (float, int)) else sign)
    if name == "luna_command":
        endpoint = data.get("endpoint")
        payload = data.get("payload", {})
        if endpoint == "luna://com.webos.service.apiadapter/audio/changeSoundOutput" and payload.get("output") == "tv_speaker":
            return "Switch to TV speakers"
        if endpoint == "luna://com.webos.notification/createToast":
            if key == "home" and action.get("pass_through") and payload.get("message") == "Glasshouse Home":
                return "Open Glasshouse Home"
            return "Show notification"
        return "Run webOS command"
    return name.replace("_", " ").capitalize() if identifier(name) else "Custom action"


def describe_bindings(config, webhooks, labels=None):
    rows = []
    for key, value in config.items():
        if not identifier(key):
            continue
        if value == "disabled":
            rows.append({"key": key, "label": "Disabled", "detail": "Pressing this key has no effect.", "enabled": False})
            continue
        actions = value if isinstance(value, list) else [value]
        parts = []
        descriptions = []
        titles = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            title = action.get("title")
            if isinstance(title, str) and title.strip():
                label = title.strip()
                titles.append(label)
            else:
                label = describe(action, webhooks, key, labels or {})
            parts.append(label)
            gesture = "Tap or hold" if action.get("allow_long_press") else "Tap"
            scope = action.get("appId")
            if identifier(scope):
                gesture += " in other apps" if scope == "!" else " in " + scope
            descriptions.append(gesture + " · " + label)
        main = titles or [part for part in parts if part != "Show notification"] or parts
        rows.append({"key": key, "label": " + ".join(dict.fromkeys(main)) or "Unassigned",
                     "enabled": bool(active_actions(value, APP_ID)), "detail": "  /  ".join(descriptions)})
    return rows


def local_labels(path):
    return json.loads(path.read_text()) if path.exists() else {}


def publish(config, app_dir=APP, labels_dir=Path(__file__).parent, control=None):
    if not app_dir.is_dir():
        return
    labels = local_labels(labels_dir / "guide-labels.json")
    rows = describe_bindings(config, local_labels(labels_dir / "webhook-labels.json"), labels)
    # A sibling script loads from the app's own origin on webOS. Never export raw actions.
    arguments = [rows, labels.get("device", "")]
    if control is not None:
        arguments.append(control)
    output = "window.receiveBindings(" + ", ".join(json.dumps(arg) for arg in arguments) + ");\n"
    with tempfile.NamedTemporaryFile(dir=str(app_dir), delete=False, mode="w") as tmp:
        staged = Path(tmp.name)
    try:
        staged.write_text(output)
        staged.chmod(0o644)
        os.replace(str(staged), str(app_dir / "bindings.js"))
    finally:
        if staged.exists():
            staged.unlink()
