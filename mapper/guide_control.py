"""Accept a key from the installed companion and run its active short-press mapping."""
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import threading

APP_ID = "me.kopiro.remoteguide"


def active_actions(binding, app):
    actions = binding if isinstance(binding, list) else [binding]
    selected = []
    matched = False
    for action in actions:
        if not isinstance(action, dict) or not action.get("function"):
            continue
        scope = action.get("appId")
        if scope == app:
            matched = True
        if scope is None or scope == app or (scope == "!" and not matched):
            selected.append(action)
    return selected


def start_control(config, dispatch):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(4)

        def log_message(self, *args):
            pass

        def reply(self, status):
            self.send_response(status)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def valid_target(self):
            host = "127.0.0.1:%d" % self.server.server_port
            return self.path == "/press" and self.headers.get("Host") == host

        def do_OPTIONS(self):
            self.reply(204 if self.valid_target() else 404)

        def do_POST(self):
            if not self.valid_target():
                return self.reply(404)
            if not hmac.compare_digest(self.headers.get("Authorization", "").encode(),
                                       ("Bearer " + token).encode()):
                return self.reply(403)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 512:
                    return self.reply(400)
                key = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeError):
                return self.reply(400)
            if not isinstance(key, str):
                return self.reply(400)
            actions = active_actions(config.get(key), APP_ID)
            if not actions:
                return self.reply(404)
            try:
                ran = dispatch(key, actions)
            except Exception:
                return self.reply(500)
            self.reply(204 if ran else 409)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, {"port": server.server_port, "token": token}


def attach(config, mapper):
    def dispatch(key, actions):
        info = mapper.luna_send("luna://com.webos.applicationManager/getForegroundAppInfo", {})
        if json.loads(info).get("appId") != APP_ID:
            return False
        if mapper.EXCLUSIVE_MODE and any(action.get("pass_through") for action in actions):
            code = mapper.get_keycode(key)
            if code is not None:
                mapper.send_keystroke(mapper.OUTPUT_DEVICE, code)
            else:
                delta = next(value for value, name in mapper.MOUSE_WHEEL.items() if name == key)
                mapper.send_input_event(mapper.OUTPUT_DEVICE, 8, delta, 2)
                mapper.send_input_event(mapper.OUTPUT_DEVICE, 0, 0, 0)
        mapper.fire_events(actions)
        return True
    return start_control(config, dispatch)[1]
