import hashlib
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mapper"))
from remote_guide import describe_bindings, publish


class GuideTest(unittest.TestCase):
    def test_actions_follow_binding_when_keys_move(self):
        url = "https://example.test/hook/private"
        aliases = {hashlib.sha256(url.encode()).hexdigest(): "Relax scene"}
        data = {"9": {"function": "post_ha_webhook", "inputs": {"url": url}}}
        row, = describe_bindings(data, aliases)
        self.assertEqual((row["key"], row["label"]), ("9", "Relax scene"))
        self.assertNotIn("private", str(row))

    def test_current_actions_and_press_semantics(self):
        rows = describe_bindings({
            "guide": "disabled", "6": {"function": "launch_app", "allow_long_press": True,
            "inputs": {"app_id": "com.webos.app.hdmi3"}}, "ch_up": {"function": "increase_oled_light",
            "inputs": {"increment": 5}}, "home": {"function": "curl", "inputs": {"url": "SECRET"}}
        }, {}, {"inputs": {"3": "Apple TV"}})
        self.assertEqual([r["label"] for r in rows], ["Disabled", "HDMI 3 · Apple TV",
                          "OLED brightness +5", "Send web request"])
        self.assertIn("hold", rows[1]["detail"])
        self.assertNotIn("SECRET", str(rows))

    @patch("remote_guide.local_labels", return_value={})
    def test_publication_tracks_removals_and_does_not_export_inputs(self, _labels):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            publish({"netflix": {"function": "run_script", "inputs": {"path": "/private/path"}}}, path)
            target = path / "bindings.js"
            self.assertNotIn("/private", target.read_text())
            publish({}, path)
            self.assertEqual(target.read_text(), "window.receiveBindings([], \"\");\n")

    def test_labels_are_optional_and_read_from_the_selected_directory(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            data = {"2": {"function": "launch_app", "inputs": {"app_id": "com.webos.app.hdmi2"}}}
            publish(data, app_dir=path, labels_dir=path)
            self.assertIn('"label": "HDMI 2"', (path / "bindings.js").read_text())
            (path / "guide-labels.json").write_text(json.dumps({
                "device": "Living room", "inputs": {"2": "Console"}
            }))
            publish(data, app_dir=path, labels_dir=path)
            result = (path / "bindings.js").read_text()
            self.assertIn('Console', result)
            self.assertTrue(result.endswith(', "Living room");\n'))
