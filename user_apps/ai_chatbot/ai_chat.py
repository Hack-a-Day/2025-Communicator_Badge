""" apps/ai_chat.py - Gemini / Groq AI chat for Hackaday Communicator Badge

Deploy: copy ai_chat.py and ai_secrets.py to /apps/ on the badge
Keyboard: type prompt -> Enter to send
F1=New conv  F2=Cycle model  F3=Tell-me-more  F4=WiFi  F5=Exit

160526 Initial port from cyberdreck
160526 Added Groq model support
160526 Added WiFi scan/pick/password UI
210526 Refactor screen to use Page framework (infobar + content + menubar)
220526 Standard demo colors; user prompts right-justified; green bg on text only
220526 Enable web search grounding (Gemini google_search; Groq web_search tool)
240526 Refactor for clarity: BgTask helper, split draw/key handling
"""

APP_NAME = "AI Chat"

import gc
import sys
import time
import _thread
import socket
import ssl
import json

if '/apps' not in sys.path:
    sys.path.insert(0, '/apps')

import lvgl
from apps.base_app import BaseApp
from hardware.keyboard import Keyboard
from ui.page import Page
from ui import styles


# ── Config ────────────────────────────────────────────────────────────────────
_GEMINI_HOST = "generativelanguage.googleapis.com"
_GROQ_HOST   = "api.groq.com"

# (display_name, f2_label, api, model_id)
_MODELS = [
    ("Gemini 2.5 flash lite", "G 2.5fl", "gemini", "gemini-2.5-flash-lite"),
    ("Gemini 2.5 flash",      "G 2.5f",  "gemini", "gemini-2.5-flash"),
    ("Groq OSS-120b",         "Groq",    "groq",   "openai/gpt-oss-120b"),
]

_SYSTEM_PROMPT = (
    "Plain text only: no markdown, no ** or * emphasis, no bullet symbols, no lists. "
    "Use short sentences. Never include URLs, citations, or source references."
)
_SEARCH_SUFFIX = (
    " When quoting current or time-sensitive information, "
    "use your web search tool to check live sources first."
)

_MAX_TOKENS  = 500
_API_TIMEOUT = 25     # seconds (HTTPS socket)
_WRAP_COLS   = 64
_HIST_LINES  = 8
_CH          = 12     # line height in px

# WiFi UI states
_WS_IDLE = 0
_WS_SCAN = 1   # scanning APs (background thread)
_WS_PICK = 2   # AP list displayed, waiting for key
_WS_PASS = 3   # password entry
_WS_CONN = 4   # connecting (background thread)

# Menubar label sets
_MENUBAR_NORMAL    = ("New", "Model", "More", "Wifi", "Exit")
_MENUBAR_WIFI_SCAN = ("",    "",      "",     "",       "Exit")
_MENUBAR_WIFI_PICK = ("",    "",      "",     "Rescan", "Exit")
_MENUBAR_WIFI_PASS = ("",    "",      "",     "",       "Exit")


# ── HTTPS ─────────────────────────────────────────────────────────────────────
def _https_post(host, path, headers, body_dict):
    """Minimal blocking HTTPS POST. Returns decoded UTF-8 body, raises on non-200."""
    body_bytes = json.dumps(body_dict).encode()
    req_lines = [
        f"POST {path} HTTP/1.1",
        f"Host: {host}",
        "Content-Type: application/json",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
    ]
    for k, v in headers.items():
        req_lines.append(f"{k}: {v}")
    req_lines += ["", ""]
    req = "\r\n".join(req_lines).encode() + body_bytes
    del body_bytes
    gc.collect()

    addr = socket.getaddrinfo(host, 443)[0][-1]
    s = socket.socket()
    s.settimeout(_API_TIMEOUT)
    try:
        s.connect(addr)
    except OSError as e:
        s.close()
        raise OSError(f"connect: {e}")
    try:
        s = ssl.wrap_socket(s, server_hostname=host)
    except OSError as e:
        s.close()
        raise OSError(f"ssl: {e}")

    mv = memoryview(req)
    sent = 0
    try:
        while sent < len(req):
            n = s.write(mv[sent:])
            if not n:
                raise OSError("write stalled")
            sent += n
    except OSError as e:
        s.close()
        raise OSError(f"write: {e}")
    del mv, req
    gc.collect()

    chunks = []
    try:
        while True:
            chunk = s.read(512)
            if not chunk:
                break
            chunks.append(bytes(chunk))
    finally:
        s.close()

    raw = b''.join(chunks)
    del chunks
    gc.collect()

    sep = raw.find(b"\r\n\r\n")
    if sep < 0:
        raise ValueError(f"No HTTP header ({len(raw)}B)")
    status = raw[:raw.find(b"\r\n")].decode()
    if " 200 " not in status:
        raise ValueError(f"HTTP {status[:60]}")
    hdr  = raw[:sep].decode().lower()
    body = bytes(raw[sep + 4:])
    del raw
    gc.collect()

    if "transfer-encoding: chunked" in hdr:
        out = bytearray()
        while body:
            end = body.find(b"\r\n")
            if end < 0:
                break
            size = int(body[:end], 16)
            if size == 0:
                break
            out += body[end + 2: end + 2 + size]
            body = body[end + 2 + size + 2:]
        body = bytes(out)
        del out

    return body.decode('utf-8', 'replace')


# ── AI API calls ──────────────────────────────────────────────────────────────
def _call_gemini(messages, model_id, api_key):
    """POST chat to Gemini. Returns the assistant reply text."""
    contents = [
        {"role": "user" if m['role'] == 'user' else "model",
         "parts": [{"text": m['text']}]}
        for m in messages
    ]
    body = {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT + _SEARCH_SUFFIX}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": _MAX_TOKENS},
        "tools": [{"google_search": {}}],
    }
    path = f"/v1beta/models/{model_id}:generateContent?key={api_key}"
    resp = _https_post(_GEMINI_HOST, path, {}, body)
    del body
    gc.collect()
    data = json.loads(resp)
    del resp
    cands = data.get("candidates", [])
    if not cands:
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidates")
        raise ValueError(f"Blocked: {reason}")
    return cands[0]["content"]["parts"][0]["text"].strip()


def _call_groq(messages, model_id, api_key):
    """POST chat to Groq (OpenAI-compatible). Returns the assistant reply text."""
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}]
    msgs += [
        {"role": "assistant" if m['role'] == 'ai' else m['role'], "content": m['text']}
        for m in messages
    ]
    body = {
        "model": model_id,
        "messages": msgs,
        "max_tokens": _MAX_TOKENS,
    }
    resp = _https_post(_GROQ_HOST, "/openai/v1/chat/completions",
                       {"Authorization": f"Bearer {api_key}"}, body)
    del body
    gc.collect()
    data = json.loads(resp)
    del resp
    choices = data.get("choices")
    if not choices:
        raise ValueError("no choices in groq response")
    content = choices[0]["message"].get("content")
    if content is None:
        raise ValueError("no content in groq response")
    return content.strip()


# ── Text helpers ──────────────────────────────────────────────────────────────
def _sanitize(text):
    """Replace common Unicode chars with ASCII equivalents."""
    for old, new in (
        ('‘', "'"), ('’', "'"), ('′', "'"),   # smart single quotes
        ('“', '"'), ('”', '"'), ('″', '"'),   # smart double quotes
        ('–', '-'), ('—', '-'), ('―', '-'),   # en/em dash
        ('‐', '-'), ('‑', '-'), ('−', '-'),   # hyphen, minus
        ('…', '...'),                                    # ellipsis
        ('•', '*'), ('·', '*'),                    # bullet, middle dot
        (' ', ' '), (' ', ' '), (' ', ' '),  # non-breaking/thin spaces
        ('​', ''), ('‌', ''), ('‍', ''),     # zero-width chars
        ('﻿', ''),                                       # BOM
    ):
        text = text.replace(old, new)
    return text


def _wrap(text, cols):
    """Word-wrap to a fixed column width. Long words are truncated, not split."""
    lines = []
    for para in text.split('\n'):
        if not para.strip():
            lines.append('')
            continue
        buf = ''
        for word in para.split():
            candidate = (buf + ' ' + word).strip() if buf else word
            if len(candidate) <= cols:
                buf = candidate
            else:
                if buf:
                    lines.append(buf)
                buf = word[:cols]
        if buf:
            lines.append(buf)
    return lines or ['']



# ── Background-thread helper ──────────────────────────────────────────────────
_PENDING = object()  # sentinel returned by BgTask.take() while still running

class BgTask:
    """One-shot background work that the UI loop polls each tick.

    Wraps a callable in a thread so the UI stays responsive. `busy`, `done`
    and `result` live in length-1 lists so the worker can mutate them
    without needing a lock.
    """

    def __init__(self):
        self.result = [None]
        self.done   = [False]
        self.busy   = False

    def start(self, fn):
        """Spawn fn() in a new thread. An exception becomes 'Error: ...'."""
        self.result[0] = None
        self.done[0]   = False
        self.busy      = True
        res, done = self.result, self.done

        def _runner():
            try:
                res[0] = fn()
            except Exception as e:
                res[0] = f'Error: {e}'
            done[0] = True

        _thread.start_new_thread(_runner, ())

    def take(self):
        """Return the result and reset if the thread has finished, else _PENDING."""
        if not (self.busy and self.done[0]):
            return _PENDING
        r = self.result[0]
        self.result[0] = None
        self.done[0]   = False
        self.busy      = False
        return r

    def discard_if_done(self):
        """Drop any pending result. Safe to call any time (e.g. on app exit)."""
        if self.busy and self.done[0]:
            self.busy = False
            self.result[0] = None
            self.done[0]   = False


# ── App ───────────────────────────────────────────────────────────────────────
class App(BaseApp):
    """Gemini / Groq AI chat with WiFi scan/pick/password UI."""

    def __init__(self, name, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 80

        # Chat state
        self._msgs   = []   # list of {role, text, meta, err}
        self._lines  = []   # wrapped render rows: {text, is_user, is_err}
        self._buf    = []   # input characters
        self._cursor = 0
        self._model_i = 0
        self._scroll_offset = 0

        # API background task + shared dot-animation timer
        self._api      = BgTask()
        self._dots     = 0
        self._dot_tick = 0

        # WiFi state
        self._wifi_state = _WS_IDLE
        self._wifi       = BgTask()
        self._wifi_aps   = []   # [(ssid, rssi), ...]
        self._wifi_ssid  = ''
        self._pw_buf     = []
        self._wifi_sel   = 0    # cursor row in PICK list

        # LVGL widgets (created in switch_to_foreground)
        self.p        = None
        self._hlabels = []
        self._ilabel  = None
        self._splash  = None
        self._splash_until = 0  # ticks_ms deadline for auto-dismiss

    def start(self):
        """Called once when the badge boots and this app is registered."""
        super().start()

    # ── Secrets ──────────────────────────────────────────────────────────────
    def _load_secrets(self):
        """Read /apps/ai_secrets.py. Values may be None or '' if missing."""
        try:
            import ai_secrets as s
            return {
                'gemini': getattr(s, 'GEMINI_KEY', None),
                'groq':   getattr(s, 'GROQ_KEY',   None),
            }
        except ImportError:
            return {'gemini': None, 'groq': None}

    # ── LVGL lifecycle ───────────────────────────────────────────────────────
    def switch_to_foreground(self):
        """Build the Page UI and reset chat state when this app gains focus."""
        super().switch_to_foreground()
        self._reset_chat_state()
        self._build_ui()

        # Greeting + secrets check
        self._note(_MODELS[self._model_i][0])
        sec = self._load_secrets()
        if not sec['gemini'] and not sec['groq']:
            self._note("Create /apps/ai_secrets.py - see README", err=True)

        try:
            import ai_wifi
            if not ai_wifi.is_connected():
                self._note("F4 for WiFi Menu")
        except Exception:
            pass

        self._redraw()

    def switch_to_background(self):
        """Drop LVGL widgets and abandon any pending API result."""
        self._wifi_state = _WS_IDLE
        self.p        = None
        self._hlabels = []
        self._ilabel  = None
        self._splash  = None
        self._api.discard_if_done()
        super().switch_to_background()

    def _reset_chat_state(self):
        self._msgs.clear()
        self._lines.clear()
        self._buf.clear()
        self._cursor = 0
        self._scroll_offset = 0

    def _build_ui(self):
        """Create all LVGL widgets for the chat screen."""
        self.p = Page()
        self.p.create_content()
        self.p.content.set_style_pad_left(8, 0)

        # Splash image (best-effort)
        try:
            from ui import graphics
            self._splash = graphics.create_image(
                "/apps/ai-chatbot-splash.png", self.p.content)
            self._splash.align(lvgl.ALIGN.TOP_LEFT, -8, 0)
            self._splash_until = time.ticks_ms() + 4000
        except Exception as e:
            print("splash:", e)
            self._splash = None

        # History labels
        self._hlabels = []
        for i in range(_HIST_LINES):
            lbl = lvgl.label(self.p.content)
            lbl.set_text("")
            lbl.align(lvgl.ALIGN.TOP_LEFT, 0, i * _CH)
            self._hlabels.append(lbl)

        # Input prompt label (sits below the history)
        self._ilabel = lvgl.label(self.p.content)
        self._ilabel.set_text("")
        self._ilabel.set_width(lvgl.pct(100))
        self._ilabel.align(lvgl.ALIGN.TOP_LEFT, 0, _HIST_LINES * _CH + 4)

        self.p.create_menubar(("New", "Model", "More", "Wifi", "Exit"))
        self.p.replace_screen()

    # ── Message history ──────────────────────────────────────────────────────
    def _note(self, text, err=False):
        """Add a meta message (status / error). Excluded from the API context."""
        self._msgs.append({'role': 'ai', 'text': text, 'meta': True, 'err': err})
        self._rebuild_lines()

    def _add(self, role, text, err=False):
        """Add a real user/AI message. Bounded to the most-recent 20 real messages."""
        if role == 'ai':
            text = _sanitize(text)
        safe = ''.join(c if 32 <= ord(c) < 128 or c == '\n' else '?' for c in text).strip()
        if not safe:
            return
        self._msgs.append({'role': role, 'text': safe, 'meta': False, 'err': err})
        while sum(1 for m in self._msgs if not m['meta']) > 20:
            for i, m in enumerate(self._msgs):
                if not m['meta']:
                    self._msgs.pop(i)
                    break
        self._rebuild_lines()

    def _rebuild_lines(self):
        self._lines = []
        for m in self._msgs:
            is_user = (m['role'] == 'user')
            is_err  = m.get('err', False)
            for seg in _wrap(m['text'], _WRAP_COLS):
                self._lines.append({'text': seg, 'is_user': is_user, 'is_err': is_err})
        if len(self._lines) > 200:
            self._lines = self._lines[-200:]

    def _api_messages(self):
        """Conversation context for the model: real user/ai turns only."""
        return [
            {'role': m['role'], 'text': m['text']}
            for m in self._msgs
            if not m['meta'] and not m['err'] and m['role'] in ('user', 'ai')
        ]

    # ── Drawing ──────────────────────────────────────────────────────────────
    def _set_menubar(self, labels):
        """Update all five menubar button labels."""
        if self.p:
            for i, text in enumerate(labels):
                self.p.set_menubar_button_label(i, text)

    def _redraw(self):
        if not self._hlabels:
            return
        if self._wifi_state != _WS_IDLE:
            self._draw_wifi()
            return
        self._set_menubar(_MENUBAR_NORMAL)
        self._maybe_hide_splash()
        if self._splash:
            return
        self._draw_history()
        self._draw_input()

    def _maybe_hide_splash(self):
        if not self._splash:
            return
        if (time.ticks_diff(time.ticks_ms(), self._splash_until) >= 0
                or any(not m.get('meta') for m in self._msgs)):
            self._clear_splash()

    def _clear_splash(self):
        if self._splash:
            self._splash.delete()
            self._splash = None

    def _visible_lines(self):
        """Return the slice of _lines that should fill the history labels (pad with None)."""
        total = len(self._lines)
        max_scroll = max(0, total - _HIST_LINES)
        if self._scroll_offset > max_scroll:
            self._scroll_offset = max_scroll
        end = total - self._scroll_offset
        start = max(0, end - _HIST_LINES)
        vis = self._lines[start:end]
        while len(vis) < _HIST_LINES:
            vis.insert(0, None)
        return vis

    def _draw_history(self):
        for i, line in enumerate(self._visible_lines()):
            lbl = self._hlabels[i]
            if line is None:
                self._style_line_empty(lbl, i)
            elif line['is_user']:
                self._style_line_user(lbl, i, line['text'])
            else:
                self._style_line_ai(lbl, i, line['text'], line['is_err'])

    def _style_line_empty(self, lbl, i):
        lbl.set_text("")
        lbl.set_style_bg_opa(0, 0)
        lbl.set_style_radius(0, 0)
        lbl.set_style_pad_left(0, 0)
        lbl.set_style_pad_right(0, 0)
        lbl.set_width(lvgl.pct(100))
        lbl.align(lvgl.ALIGN.TOP_LEFT, 0, i * _CH)

    def _style_line_user(self, lbl, i, text):
        # Green rounded "bubble" hugging the text, right-justified
        lbl.set_text(text)
        lbl.set_width(lvgl.SIZE_CONTENT)
        lbl.align(lvgl.ALIGN.TOP_RIGHT, 0, i * _CH)
        lbl.set_style_bg_color(styles.lvg_color_green, 0)
        lbl.set_style_bg_opa(255, 0)
        lbl.set_style_radius(5, 0)
        lbl.set_style_pad_left(3, 0)
        lbl.set_style_pad_right(3, 0)
        lbl.set_style_text_color(styles.hackaday_white, 0)
        lbl.set_style_text_align(lvgl.TEXT_ALIGN.LEFT, 0)

    def _style_line_ai(self, lbl, i, text, is_err):
        # Plain text, full-width, red if error
        lbl.set_text(text)
        lbl.set_width(lvgl.pct(100))
        lbl.align(lvgl.ALIGN.TOP_LEFT, 0, i * _CH)
        lbl.set_style_bg_opa(0, 0)
        lbl.set_style_radius(0, 0)
        lbl.set_style_pad_left(0, 0)
        lbl.set_style_pad_right(0, 0)
        lbl.set_style_text_color(
            styles.lvg_color_red if is_err else styles.lcd_color_fg, 0)
        lbl.set_style_text_align(lvgl.TEXT_ALIGN.LEFT, 0)

    def _draw_input(self):
        if not self._ilabel:
            return
        if self._api.busy:
            self._ilabel.set_text("Waiting...")
        else:
            txt  = ''.join(self._buf)
            cpos = self._cursor
            self._ilabel.set_text(('> ' + txt[:cpos] + '_' + txt[cpos:])[:_WRAP_COLS])
        self._ilabel.set_style_text_color(styles.lcd_color_fg, 0)
        self._ilabel.set_style_text_align(lvgl.TEXT_ALIGN.LEFT, 0)

    def _draw_wifi(self):
        """Render the current WiFi UI state (called only when state != IDLE)."""
        if not self._hlabels:
            return
        for idx, lbl in enumerate(self._hlabels):
            lbl.set_text("")
            lbl.set_width(lvgl.pct(100))
            lbl.align(lvgl.ALIGN.TOP_LEFT, 0, idx * _CH)
            lbl.set_style_bg_opa(0, 0)
            lbl.set_style_text_color(styles.lcd_color_fg, 0)
            lbl.set_style_text_align(lvgl.TEXT_ALIGN.LEFT, 0)

        st = self._wifi_state
        if st == _WS_SCAN:
            self._set_menubar(_MENUBAR_WIFI_SCAN)
            self._hlabels[0].set_text("Scanning WiFi" + '.' * self._dots)
        elif st == _WS_PICK:
            self._set_menubar(_MENUBAR_WIFI_PICK)
            self._hlabels[0].set_text("Select WiFi with cursor keys. Hit Enter")
            for i, (ssid, rssi) in enumerate(self._wifi_aps[:_HIST_LINES - 1]):
                prefix = '>' if i == self._wifi_sel else ' '
                self._hlabels[i + 1].set_text(
                    f"{prefix} {ssid[:22]} {rssi}dB"
                )
        elif st == _WS_PASS:
            self._set_menubar(_MENUBAR_WIFI_PASS)
            self._hlabels[0].set_text(f"Enter password for: {self._wifi_ssid[:40]}")
            self._hlabels[1].set_text("Enter=connect")
            self._hlabels[2].set_text("")
            if self._ilabel:
                self._ilabel.set_text('> ' + ''.join(self._pw_buf) + '_')
                self._ilabel.set_style_text_color(styles.lcd_color_fg, 0)
                self._ilabel.set_style_text_align(lvgl.TEXT_ALIGN.LEFT, 0)
        elif st == _WS_CONN:
            self._set_menubar(_MENUBAR_WIFI_SCAN)
            self._hlabels[0].set_text("Connecting to:")
            self._hlabels[1].set_text(f"  {self._wifi_ssid[:30]}")
            self._hlabels[2].set_text('  ' + '.' * self._dots)

        if st != _WS_PASS and self._ilabel:
            self._ilabel.set_text("")

    # ── Polled by the badge framework ────────────────────────────────────────
    def run_foreground(self):
        """Polled every foreground_sleep_ms while this app is in focus."""
        if self._wifi_state != _WS_IDLE:
            self._handle_wifi_ui()
            return

        # API thread finished: append the reply and redraw
        reply = self._api.take()
        if reply is not _PENDING:
            self._scroll_offset = 0
            text = reply or 'Error: no response'
            self._add('ai', text, err=text.startswith('Error'))
            self._redraw()
            return

        # API still running: animate dots
        if self._api.busy:
            self._tick_dots(700, prefix="Waiting")
            return

        # Splash visible: auto-dismiss on timer, or discard any keypress and show prompt
        if self._splash:
            if time.ticks_diff(time.ticks_ms(), self._splash_until) >= 0:
                self._redraw()
                return
            kb = self.badge.keyboard
            consumed = [kb.f1(), kb.f2(), kb.f3(), kb.f4(), kb.f5(), kb.read_key()]
            if any(consumed):
                self._clear_splash()
                self._redraw()
            return

        if self._handle_fkeys():
            return
        self._handle_typing()

    def run_background(self):
        """Drop late results from any thread the user has already abandoned."""
        self._api.discard_if_done()
        self._wifi.discard_if_done()

    # ── Shared dot-animation timer ───────────────────────────────────────────
    def _tick_dots(self, period_ms, prefix=None):
        """Advance the dot counter on a fixed timer. If prefix is set, update _ilabel."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self._dot_tick) < period_ms:
            return
        self._dots = (self._dots % 3) + 1
        self._dot_tick = now
        if prefix and self._ilabel:
            self._ilabel.set_text(f"{prefix}{'.' * self._dots}")

    # ── F-key handling ───────────────────────────────────────────────────────
    def _handle_fkeys(self):
        """Returns True if an F-key was consumed this tick."""
        kb = self.badge.keyboard
        if kb.f1():
            self._new_conversation()
        elif kb.f2():
            self._cycle_model()
        elif kb.f3():
            self._clear_splash()
            self._send("Tell me more")
        elif kb.f4():
            self._clear_splash()
            self._start_wifi_scan()
        elif kb.f5():
            self.switch_to_background()
        else:
            return False
        return True

    def _new_conversation(self):
        self._clear_splash()
        self._reset_chat_state()
        self._note(f"New conv - {_MODELS[self._model_i][0]}")
        self._redraw()

    def _cycle_model(self):
        self._clear_splash()
        self._model_i = (self._model_i + 1) % len(_MODELS)
        self._note(f"Model: {_MODELS[self._model_i][0]}")
        self._redraw()

    # ── Typing ───────────────────────────────────────────────────────────────
    def _handle_typing(self):
        key = self.badge.keyboard.read_key()
        if key is None:
            return
        self._clear_splash()

        if key == '\n':
            self._send()
            return   # _send already redraws

        if self._apply_edit_key(key):
            self._redraw()

    def _apply_edit_key(self, key):
        """Mutate input buffer / cursor / scroll for one keypress. Returns True if redraw needed."""
        if key == '\b':
            if self._cursor > 0:
                self._buf.pop(self._cursor - 1)
                self._cursor -= 1
            return True
        if key == '\x7f':
            if self._cursor < len(self._buf):
                self._buf.pop(self._cursor)
            return True
        if key == Keyboard.UP:
            max_scroll = max(0, len(self._lines) - _HIST_LINES)
            self._scroll_offset = min(self._scroll_offset + _HIST_LINES, max_scroll)
            return True
        if key == Keyboard.DOWN:
            self._scroll_offset = max(0, self._scroll_offset - _HIST_LINES)
            return True
        if key == Keyboard.LEFT:
            if self._cursor > 0:
                self._cursor -= 1
            return True
        if key == Keyboard.RIGHT:
            if self._cursor < len(self._buf):
                self._cursor += 1
            return True
        if key == Keyboard.ESC:
            self._buf.clear()
            self._cursor = 0
            return True
        if len(key) == 1 and ord(key) >= 32 and len(self._buf) < 200:
            self._buf.insert(self._cursor, key)
            self._cursor += 1
            return True
        return False

    # ── Sending a prompt ─────────────────────────────────────────────────────
    def _send(self, text=None):
        if text is None:
            text = ''.join(self._buf).strip()
        self._buf.clear()
        self._cursor = 0
        self._scroll_offset = 0

        if not text:
            if not self._msgs:
                return
            text = "Tell me more"

        sec = self._load_secrets()
        _, _, api_type, model_id = _MODELS[self._model_i]
        api_key = sec.get(api_type)
        if not api_key:
            self._note(f"No {api_type.upper()}_KEY in ai_secrets.py", err=True)
            self._redraw()
            return

        self._add('user', text)
        self._dots     = 0
        self._dot_tick = time.ticks_ms()
        self._api.start(self._build_api_job(sec, api_type, model_id, api_key))
        self._redraw()

    def _build_api_job(self, sec, api_type, model_id, api_key):
        """Closure executed on the worker thread: connect WiFi, then call the AI."""
        msgs = self._api_messages()

        def job():
            import ai_wifi
            if not ai_wifi.ensure_connected():
                return 'Error: no WiFi - press F4 to connect'
            if api_type == 'gemini':
                return _call_gemini(msgs, model_id, api_key)
            return _call_groq(msgs, model_id, api_key)

        return job

    # ── WiFi state machine ───────────────────────────────────────────────────
    def _start_wifi_scan(self):
        self._wifi_state = _WS_SCAN
        self._dots       = 0
        self._dot_tick   = time.ticks_ms()
        self._draw_wifi()

        def job():
            try:
                import ai_wifi
                return ai_wifi.scan_aps()
            except Exception:
                return []

        self._wifi.start(job)

    def _start_wifi_conn(self):
        self._wifi_state = _WS_CONN
        self._dots       = 0
        self._dot_tick   = time.ticks_ms()
        self._draw_wifi()

        ssid = self._wifi_ssid
        pw   = ''.join(self._pw_buf)

        def job():
            import ai_wifi
            ok = ai_wifi.connect(ssid, pw)
            if ok:
                ai_wifi.insert_cred(ssid, pw)
            return ok

        self._wifi.start(job)

    def _handle_wifi_ui(self):
        """Dispatch one tick of the WiFi state machine. F5 always escapes."""
        if self.badge.keyboard.f5():
            self._wifi_state = _WS_IDLE
            self._redraw()
            return

        st = self._wifi_state
        if st == _WS_SCAN:
            self._wifi_step_scan()
        elif st == _WS_PICK:
            self._wifi_step_pick()
        elif st == _WS_PASS:
            self._wifi_step_pass()
        elif st == _WS_CONN:
            self._wifi_step_conn()

    def _wifi_step_scan(self):
        result = self._wifi.take()
        if result is _PENDING:
            self._tick_dots(500)
            self._draw_wifi()
            return

        aps = result if isinstance(result, list) else []
        self._wifi_aps = aps
        if aps:
            self._wifi_state = _WS_PICK
            self._wifi_sel   = 0
            self._draw_wifi()
        else:
            self._wifi_state = _WS_IDLE
            self._note("WiFi: no networks found", err=True)
            self._redraw()

    def _wifi_step_pick(self):
        # F4 = Rescan
        if self.badge.keyboard.f4():
            self._start_wifi_scan()
            return

        key = self.badge.keyboard.read_key()
        if key in (Keyboard.ESC, '\x1b'):
            self._wifi_state = _WS_IDLE
            self._redraw()
        elif key == Keyboard.UP:
            self._wifi_sel = max(0, self._wifi_sel - 1)
            self._draw_wifi()
        elif key == Keyboard.DOWN:
            self._wifi_sel = min(min(len(self._wifi_aps), _HIST_LINES - 1) - 1, self._wifi_sel + 1)
            self._draw_wifi()
        elif key == '\n':
            if 0 <= self._wifi_sel < len(self._wifi_aps):
                self._wifi_ssid = self._wifi_aps[self._wifi_sel][0]
                self._pw_buf = self._stored_password(self._wifi_ssid)
                self._wifi_state = _WS_PASS
                self._draw_wifi()

    def _stored_password(self, ssid):
        """Look up a previously-saved password for ssid (as a list of chars)."""
        try:
            import ai_wifi
            ai_wifi.load_creds()
            stored = ai_wifi.find_pass(ssid)
        except Exception:
            stored = None
        return list(stored) if stored else []

    def _wifi_step_pass(self):
        key = self.badge.keyboard.read_key()
        if key is None:
            return
        if key in (Keyboard.ESC, '\x1b'):
            self._wifi_state = _WS_PICK
            self._draw_wifi()
        elif key == '\n':
            self._start_wifi_conn()
        elif key in ('\b', '\x7f') and self._pw_buf:
            self._pw_buf.pop()
            self._draw_wifi()
        elif len(key) == 1 and ord(key) >= 32 and len(self._pw_buf) < 63:
            self._pw_buf.append(key)
            self._draw_wifi()

    def _wifi_step_conn(self):
        result = self._wifi.take()
        if result is _PENDING:
            self._tick_dots(500)
            self._draw_wifi()
            return

        self._wifi_state = _WS_IDLE
        if result is True:
            try:
                import ai_wifi
                self._note(f"WiFi: connected ({ai_wifi.rssi()}dBm)")
            except Exception:
                self._note("WiFi: connected")
        else:
            self._note("WiFi: failed to connect", err=True)
        self._redraw()
