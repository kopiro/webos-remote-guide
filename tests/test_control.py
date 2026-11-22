import json
import sys
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mapper"))
from guide_control import APP_ID, attach, start_control
from remote_guide import describe_bindings


class CompanionTest(unittest.TestCase):
    def test_sequence_title_and_detail(self):
        row, = describe_bindings({"5": [
            {"function": "luna_command", "inputs": {"endpoint": "luna://com.webos.notification/createToast"}},
            {"function": "launch_app", "title": "  My favorite app  ", "inputs": {"app_id": "demo"}}
        ]}, {})
        self.assertEqual(row["label"], "My favorite app")
        self.assertIn("Show notification", row["detail"])
        self.assertIn("My favorite app", row["detail"])

    def test_only_configured_short_presses_reach_dispatch(self):
        dispatch = Mock(return_value=True)
        matching = {"function": "toggle", "appId": APP_ID}
        config = {"8": [matching, {"function": "other", "appId": "!"}],
                  "0": "disabled", "7": {"function": "other", "appId": "other"}}
        server, channel = start_control(config, dispatch)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def post(key, token):
            client = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            try:
                client.request("POST", "/press", json.dumps(key), {"Authorization": "Bearer " + token})
                return client.getresponse().status
            finally:
                client.close()

        self.assertEqual(post("8", "wrong"), 403)
        for key in ("missing", "0", "7"):
            self.assertEqual(post(key, channel["token"]), 404)
        self.assertEqual(post({"function": "custom"}, channel["token"]), 400)
        dispatch.assert_not_called()
        self.assertEqual(post("8", channel["token"]), 204)
        dispatch.assert_called_once_with("8", [matching])

    def test_foreground_and_native_pass_through(self):
        mapper = Mock(EXCLUSIVE_MODE=True, OUTPUT_DEVICE="output")
        with patch("guide_control.start_control", return_value=(None, {})) as start:
            attach({}, mapper)
        dispatch = start.call_args.args[1]
        actions = [{"function": "toast", "pass_through": True}]
        mapper.luna_send.return_value = '{"appId":"another.app"}'
        self.assertFalse(dispatch("home", actions))
        mapper.fire_events.assert_not_called()
        mapper.send_keystroke.assert_not_called()
        mapper.luna_send.return_value = json.dumps({"appId": APP_ID})
        mapper.get_keycode.return_value = 773
        self.assertTrue(dispatch("home", actions))
        mapper.send_keystroke.assert_called_once_with("output", 773)
        mapper.fire_events.assert_called_once_with(actions)
