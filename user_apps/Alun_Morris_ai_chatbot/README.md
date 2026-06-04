# AI Chat — Hackaday 2025 Communicator Badge

A Gemini / Groq AI chat app for the [Hackaday 2025 Communicator Badge](https://hackaday.io/project/200652), running on MicroPython with an LVGL display.

![Splash screen showing a robot head icon and the active model name](ai-chatbot-splash.png)

## Features

- Chat free with **Gemini 2.5 Flash Lite**, **Gemini 2.5 Flash**, or **Groq OSS-120b**
- **Web search grounding** — Gemini uses the `google_search` tool for live results with Gemini
- **WiFi manager** — scan, select, and connect to networks from the badge; credentials saved to NVS flash
- Right-justified green chat bubbles for user prompts
- Up/Down scrolling through chat history
- Cycle models mid-conversation without losing context

![AI chat session on the badge](chat-session.jpeg)

## Files

| File | Deploy to | Purpose |
|------|-----------|---------|
| `ai_chat.py` | `/apps/ai_chat.py` | Main app |
| `ai_wifi.py` | `/apps/ai_wifi.py` | WiFi manager |
| `ai_secrets.py` | `/apps/ai_secrets.py` | API keys and WiFi credentials (gitignored) |
| `ai-chatbot-splash.png` | `/apps/ai-chatbot-splash.png` | Startup splash image |

## Setup

### 1. Get API keys

- **Gemini**: [Google AI Studio](https://aistudio.google.com/app/apikey) — free tier
- **Groq**: [Groq Console](https://console.groq.com/) — free tier, fast inference

### 2. Create `ai_secrets.py`

Copy the template below and fill in your keys:

```python
# /apps/ai_secrets.py

GEMINI_KEY = "..."
GROQ_KEY   = "..."
```

### 3. Upload to the badge

See [github.com/Hack-a-Day/2025-Communicator_Badge/tree/main/firmware#syncing-to-the-badge](https://github.com/Hack-a-Day/2025-Communicator_Badge/tree/main/firmware#syncing-to-the-badge)
```bash
mpremote cp ai_chat.py           :/apps/ai_chat.py
mpremote cp ai_wifi.py          :/apps/ai_wifi.py
mpremote cp ai_secrets.py       :/apps/ai_secrets.py
mpremote cp ai-chatbot-splash.png :/apps/ai-chatbot-splash.png
```

Then power-cycle the badge.


The badge auto-discovers user apps whose class is named `App` in `/apps/`.

## Controls

| Key | Action |
|-----|--------|
| Type + **Enter** | Send prompt |
| **F1** | New conversation |
| **F2** | Cycle AI model |
| **F3** | "Tell me more" |
| **F4** | WiFi menu (scan / connect) |
| **F5** | Exit to home screen |
| **↑ / ↓** | Scroll chat history (chat) or move cursor (WiFi pick) |
| **← / →** | Move cursor in input |
| **Backspace** | Delete left of cursor |
| **Esc** | Clear input / go back in WiFi UI |

## WiFi

Press **F4** to scan for networks, select with cursor keys, enter the password, and press Enter to connect. Credentials are saved to NVS flash and used automatically on subsequent connections.

## Architecture

```
ai_chat.py
├── _https_post()       raw HTTPS POST over MicroPython sockets
├── _call_gemini()      Gemini generateContent API (with google_search grounding)
├── _call_groq()        Groq OpenAI-compatible chat completions API
├── _sanitize()         Unicode → ASCII substitution for AI replies
├── BgTask              threads AI/WiFi calls; UI polls .take() each 80 ms tick
└── App(BaseApp)
    ├── switch_to_foreground / switch_to_background   LVGL lifecycle
    ├── _build_ui                  create Page, labels, menubar
    ├── _draw_history / _draw_wifi render chat or WiFi UI
    ├── run_foreground             polled loop: keys, API result, dot animation
    ├── _send / _build_api_job     dispatch prompt to background thread
    └── _wifi_step_*               WiFi state machine (scan→pick→pass→conn)
```

## Requirements

- Hackaday 2025 Communicator Badge (ESP32-S3, MicroPython, LVGL)
- Badge firmware with `ui.page`, `ui.styles`, `ui.graphics`, `apps.base_app`
