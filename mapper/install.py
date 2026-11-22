"""Install the display-only export hook after installing the IPK."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from remote_guide import APP, publish

ROOT = Path("/home/root")
MAPPER = ROOT / "magic_mapper.py"
PACKAGE = Path(__file__).parent
ANCHOR = "        button_map = json.load(config_file)\n"
HOOK = """    try:
        from remote_guide import publish
        publish(button_map)
    except Exception as error:
        print("Remote Guide export unavailable: %s" % type(error).__name__)
"""


def install_file(dest, content, mode):
    with tempfile.NamedTemporaryFile(dir=str(dest.parent), delete=False) as staged:
        staged.write(content)
        staged.flush()
        os.fchmod(staged.fileno(), mode)
    os.replace(staged.name, str(dest))


def main():
    source = MAPPER.read_bytes()
    current = source.decode()
    if current.count(ANCHOR) != 1 or "def get_button_map():" not in current:
        raise SystemExit("Unrecognized Magic Mapper config loader")
    if not APP.is_dir():
        raise SystemExit("Install the Remote Guide IPK first")
    install_file(ROOT / "remote_guide.py", (PACKAGE / "remote_guide.py").read_bytes(), 0o600)
    for name in ("webhook-labels.json", "guide-labels.json"):
        if (PACKAGE / name).is_file():
            install_file(ROOT / name, (PACKAGE / name).read_bytes(), 0o600)
    with (ROOT / "magic_mapper_config.json").open() as config:
        publish(json.load(config), labels_dir=ROOT)
    if ANCHOR + HOOK not in current:
        # Recognize the previous exporter by its complete hook, independent of its module prefix.
        hook_pattern = re.escape(ANCHOR + HOOK).replace("remote_guide", r"[A-Za-z_]\w*_remote_guide", 1)
        modified, replaced = re.subn(hook_pattern, lambda _: ANCHOR + HOOK, current, count=1)
        if not replaced:
            modified = current.replace(ANCHOR, ANCHOR + HOOK)
        compile(modified, str(MAPPER), "exec")
        backup = ROOT / ("magic_mapper.py.before-remote-guide-" + hashlib.sha256(source).hexdigest()[:12])
        if not backup.exists():
            shutil.copy2(MAPPER, backup)
        if backup.read_bytes() != source or MAPPER.read_bytes() != source:
            raise SystemExit("Magic Mapper changed during installation")
        install_file(MAPPER, modified.encode(), stat.S_IMODE(MAPPER.stat().st_mode))
    print("Remote Guide projection installed")


if __name__ == "__main__":
    main()
