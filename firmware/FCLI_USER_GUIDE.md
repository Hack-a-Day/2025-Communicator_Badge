# FCLI User Guide

Flipper-style CLI (FCLI) is the badge USB serial command interface for radio, network, storage, and hardware operations.

This guide is written as a reference manual. It is intended to be read like API documentation: command contract first, examples second.

## Contents

- [1. Scope](#1-scope)
- [2. Transport and Session Lifecycle](#2-transport-and-session-lifecycle)
	- [2.1 Serial Transport](#21-serial-transport)
	- [2.2 Session Startup](#22-session-startup)
	- [2.3 Session Termination](#23-session-termination)
	- [2.4 Access Methods](#24-access-methods)
- [3. Shell Contract](#3-shell-contract)
	- [3.0 Notation Conventions](#30-notation-conventions)
	- [3.1 Command Grammar](#31-command-grammar)
	- [3.2 Discovery](#32-discovery)
	- [3.3 Interactive Features](#33-interactive-features)
	- [3.4 Error Model](#34-error-model)
- [4. Command Reference](#4-command-reference)
	- [4.0 Available Commands at a Glance](#40-available-commands-at-a-glance)
	- [4.1 System Commands](#41-system-commands)
	- [4.2 LoRa Group](#42-lora-group)
	- [4.3 Radio Group](#43-radio-group)
	- [4.4 Sub-GHz Group](#44-sub-ghz-group)
	- [4.5 Net Group](#45-net-group)
	- [4.6 Chat Group](#46-chat-group)
	- [4.7 Storage Group](#47-storage-group)
	- [4.8 Hardware Groups](#48-hardware-groups)
	- [4.9 Wireless Discovery Groups](#49-wireless-discovery-groups)
	- [4.10 App, Config, and Misc Groups](#410-app-config-and-misc-groups)
- [5. Operational Playbooks](#5-operational-playbooks)
	- [5.0 Reading Logs via CLI](#50-reading-logs-via-cli)
	- [5.1 Chatting with Other Badges](#51-chatting-with-other-badges)
	- [5.2 Health and RF Baseline](#52-health-and-rf-baseline)
	- [5.3 Capture and Replay Validation](#53-capture-and-replay-validation)
	- [5.4 Serial File Exchange](#54-serial-file-exchange)
- [6. Security, Safety, and Compliance](#6-security-safety-and-compliance)
- [7. Troubleshooting Reference](#7-troubleshooting-reference)
- [8. Testing and Validation](#8-testing-and-validation)
- [9. Implementation Pointers for Contributors](#9-implementation-pointers-for-contributors)

## 1. Scope

FCLI provides:

- Serial shell access to badge runtime and peripherals
- Grouped commands with discoverable help
- Interactive and streaming workflows
- Scriptable command execution via batch files

FCLI does not provide:

- A security boundary between commands
- Region-specific RF compliance enforcement
- Guaranteed availability of every command on every firmware build

## 2. Transport and Session Lifecycle

### 2.1 Serial Transport

- Interface: USB CDC serial
- Default baud: 115200
- Expected terminal mode: UTF-8, CRLF or LF accepted

### 2.2 Session Startup

1. Connect badge over USB.
2. Open serial terminal at 115200.
3. Press Enter until prompt appears.

Prompt format:

```text
badge [/] >:
```

### 2.3 Session Termination

- Use `exit` to drop to MicroPython REPL.
- Use device reboot to restart the shell process.

### 2.4 Access Methods

This section follows a Flipper-style onboarding pattern: multiple valid ways to access CLI depending on your toolchain.

Method 1: VS Code Serial Monitor

1. Connect badge over USB.
2. Open VS Code terminal or serial monitor extension.
3. Select the badge COM port.
4. Set baud to 115200.
5. Press Enter to get prompt.

Method 2: Standalone serial terminal

Windows with PuTTY:

1. Connect badge over USB.
2. Open Device Manager and note COM port.
3. Start PuTTY.
4. Select Serial connection.
5. Enter COM port and speed 115200.
6. Open session and press Enter.

Linux with screen:

```bash
ls /dev/serial/by-id/
screen /dev/serial/by-id/<device-id> 115200
```

macOS with screen:

```bash
ls /dev/cu.*
screen /dev/cu.usbmodemXXXX 115200
```

Method 3: minicom

```bash
minicom -D /dev/ttyACM0 -b 115200
```

If another process already owns the serial port, close it first.

## 3. Shell Contract

### 3.0 Notation Conventions

- `<required>` means required argument.
- `[optional]` means optional argument.
- `A|B` means either A or B.
- `...` means repeated values.

### 3.1 Command Grammar

Syntax:

```text
<command>
<group> <subcommand> [arg1] [arg2] ...
```

Quoted strings are supported:

```text
chat send "hello world"
```

### 3.2 Discovery

- `help`: lists top-level commands and groups
- `?`: alias of `help`
- `<group> ?`: lists subcommands in a group

### 3.3 Interactive Features

- History: up and down arrows
- Tab completion: command and some path-aware completion
- Interrupt: `Ctrl+C` to stop streaming commands

### 3.4 Error Model

Most commands follow this behavior:

- Invalid syntax: prints `Usage:` line
- Invalid argument value: prints `Error:` line
- Hardware/runtime exceptions: catches and prints `Error: <detail>`

## 4. Command Reference

## 4.0 Available Commands at a Glance

| Category | Groups/Commands |
|---|---|
| Shell/System | help, ?, version, uptime, date, free, top, clear, history, batch, exit |
| Radio | lora, radio, subghz |
| Networking | net, chat |
| Storage | storage |
| Hardware | i2c, gpio, led, display, input |
| Wireless Discovery | wifi, ble, wardriving |
| Runtime Control | loader, config, crypto, power, badusb |

Use `help` to enumerate exactly what your build exposes.

## 4.1 System Commands

Synopsis:

- Shell utilities and runtime diagnostics.

Commands:

- `help`, `?`, `version`, `uptime`, `date`, `free`, `top`, `clear`, `history`, `batch`, `exit`

Parameters:

- `batch <file_path>`: line-based command script path.
- Other commands in this group are parameterless.

Output:

- Human-readable status lines, tables, and diagnostics.
- `top` streams repeated status output until interrupted.

Errors:

- Missing/invalid file path for `batch`.
- Platform limitations for RTC or memory detail commands.

Examples:

```text
help
free
top
batch /scripts/startup.cli
```

See Also:

- `history`
- `clear`
- `log`

## 4.2 LoRa Group

Synopsis:

- High-level LoRa operations integrated with BadgeNet workflows.

Commands:

- `lora info`
- `lora freq [slot]`
- `lora tx <hex_payload>`
- `lora rx`
- `lora rx_raw`
- `lora chat [slot]`

Parameters:

- `slot`: integer frequency slot.
- `hex_payload`: even-length hexadecimal payload bytes.

Output:

- Radio configuration/status lines.
- Streaming receive output for `rx` and `rx_raw`.

Errors:

- Invalid slot values.
- Invalid hexadecimal payload for `tx`.
- Chat wrapper unavailable if Chat app is not active.

Examples:

```text
lora info
lora freq 9
lora tx 48454C4C4F
```

See Also:

- `radio info`
- `chat status`
- `net sniff`

## 4.3 Radio Group

Synopsis:

- Low-level SX1262 parameter controls.

Commands:

- `radio info`
- `radio set_freq <mhz>`
- `radio set_power <dbm>`
- `radio set_sf <factor>`
- `radio set_bw <khz>`
- `radio freq_slot <slot>`
- `radio rssi`

Parameters:

- `mhz`: 150.0 to 960.0
- `dbm`: -9 to 22
- `factor`: 7 to 12
- `khz`: greater than 0 and up to 500
- `slot`: 1 to 52

Output:

- Confirmation lines for updated fields.
- Current radio details from `info`.

Errors:

- Out-of-range numeric values.
- Unsupported operation when hardware method is unavailable.

Examples:

```text
radio set_freq 915.0
radio set_power 14
radio set_sf 9
radio set_bw 250
radio rssi
```

See Also:

- `lora info`
- `subghz record`

## 4.4 Sub-GHz Group

Synopsis:

- Sub-GHz capture, scan, and replay workflows.

Commands:

- `subghz rx <freq_mhz>`
- `subghz tx <freq_mhz> <hex_data>`
- `subghz scan`
- `subghz record <freq_mhz> <duration_s> <file.sub>`
- `subghz replay <file.sub> [repeat] [freq_mhz]`
- `subghz play ...` (compatibility alias)

Parameters:

- `freq_mhz`: frequency in MHz.
- `duration_s`: capture duration in seconds.
- `file.sub`: sub-file capture path.
- `repeat`: optional replay count.

Output:

- Capture/replay status and packet counts.
- Streaming scan output for `scan`.

Errors:

- Missing or malformed capture files.
- Unsupported OOK helper methods on certain builds.
- Invalid numeric conversion for frequency/duration/repeat.

Examples:

```text
subghz record 433.92 10 demo.sub
subghz replay demo.sub
subghz replay demo.sub 3
subghz replay demo.sub 1 433.92
subghz play 433.92 demo.sub 1
```

See Also:

- `radio set_freq`
- `storage stat`
- `storage xsend`

## 4.5 Net Group

Synopsis:

- BadgeNet network diagnostics and packet observation.

Commands:

- `net address`
- `net ping [address_hex]`
- `net nodes`
- `net send <port> <hex_payload>`
- `net sniff [--pcap <file>]`

Parameters:

- `address_hex`: optional hex destination.
- `port`: integer protocol port.
- `hex_payload`: payload bytes in hex.
- `--pcap <file>`: optional pcap output path.

Output:

- Node lists and addresses.
- Packet stream lines while sniffing.

Errors:

- Invalid hex values or invalid port.
- Network stack unavailable in constrained/test environments.

Examples:

```text
net address
net nodes
net send 42 AABBCCDD
net sniff --pcap /captures/net.pcap
```

See Also:

- `lora rx`
- `chat status`

## 4.6 Chat Group

Synopsis:

- Serial wrapper around active Chat app state.

Commands:

- `chat status`
- `chat send <message_text>`
- `chat history`
- `chat channel [freq] [topic]`

Parameters:

- `message_text`: full trailing text payload.
- `freq`, `topic`: optional integer channel fields.

Output:

- Channel info, message history, and send confirmations.

Errors:

- Chat app not running.
- Invalid channel argument values.

Examples:

```text
chat status
chat send Hello mesh
chat channel 9 1
chat history
```

See Also:

- `lora chat`
- `lora freq`

## 4.7 Storage Group

Synopsis:

- Filesystem operations and serial file transfer tools.

Commands:

- `storage list [path]`, `read <path>`, `write <path> <text>`, `append <path> <text>`
- `storage stat <path>`, `md5 <path>`, `mkdir <path>`, `remove <path>`
- `storage cd [path]`, `pwd`
- `storage pull <path>`, `push <path> <base64>`
- `storage xsend <path>`, `xreceive <path>`

Parameters:

- `path`: absolute or relative to shell working directory.
- `base64`: valid base64 payload.

Output:

- File listings, metadata, and transfer confirmations.
- Base64 chunk stream for `pull`.

Errors:

- Missing paths, invalid base64, and filesystem errors.
- XMODEM transfer failures when host tool mode mismatches.

Examples:

```text
storage list /
storage read /config.txt
storage write /notes.txt hello
storage md5 /notes.txt
storage xsend /captures/demo.sub
```

See Also:

- `subghz record`
- `subghz replay`

## 4.8 Hardware Groups

Synopsis:

- Peripheral and physical IO inspection groups.

### Template Legend

- Each subgroup follows: Synopsis, Commands, Parameters, Output, Errors, Examples, See Also.

### 4.8.1 i2c

Synopsis:

- SAO I2C bus scan and dump utilities.

Commands:

- `i2c scan`
- `i2c dump <addr> <size>`

Parameters:

- `addr`: decimal or hex I2C address.
- `size`: byte count to read.

Output:

- Address list or formatted byte dump.

Errors:

- Invalid address/size and device access failures.

Examples:

```text
i2c scan
i2c dump 0x50 64
```

See Also:

- `gpio read`

### 4.8.2 gpio

Synopsis:

- SAO GPIO mode, read, write, and basic sampling.

Commands:

- `gpio mode <pin> <in|out>`
- `gpio set <pin> <0|1>`
- `gpio read <pin>`
- `gpio logic <pin> <samples> [delay_ms]`

Parameters:

- `pin`: mapped pin token or numeric pin value.
- `samples`: integer sample count.
- `delay_ms`: optional delay between samples.

Output:

- Pin state confirmations and sampled trace text.

Errors:

- Unknown pin mapping.
- Invalid mode/value/sample arguments.

Examples:

```text
gpio mode sao1 out
gpio set sao1 1
gpio read sao2
gpio logic sao1 20 5
```

See Also:

- `i2c scan`
- `led set`

### 4.8.3 led

Synopsis:

- Debug LED state control.

Commands:

- `led set <0|1>`

Parameters:

- `0`: off
- `1`: on

Output:

- LED state confirmation line.

Errors:

- Unsupported LED backend on specific builds.

Examples:

```text
led set 1
led set 0
```

See Also:

- `display backlight`

### 4.8.4 display

Synopsis:

- Direct display rendering and backlight control.

Commands:

- `display text <x> <y> <text>`
- `display clear`
- `display backlight <0..1023>`
- `display image [x] [y] <path>`

Parameters:

- `x`, `y`: pixel coordinates.
- `path`: image path on badge filesystem.

Output:

- Render and brightness confirmation messages.

Errors:

- Invalid numeric conversion for coordinates/brightness.
- Missing or unreadable image file.

Examples:

```text
display text 0 0 CLI active
display backlight 700
display image /images/logo.bin
display clear
```

See Also:

- `input send_text`

### 4.8.5 input

Synopsis:

- Keyboard event injection and queue debugging.

Commands:

- `input send <key_token>`
- `input send_text <text>`
- `input dump [count]`

Parameters:

- `key_token`: named key (for example ENTER, ESC, LEFT) or literal token.
- `count`: optional max events to print.

Notes:

- `input dump` with no count prints a single snapshot and returns immediately.
- `input dump <count>` streams up to the requested number of events.

Output:

- Injection confirmations and queued event stream.

Errors:

- Invalid count values.

Examples:

```text
input send ENTER
input send ESC
input send LEFT
input send_text hello
input dump 10
```

See Also:

- `display text`
- `chat send`

## 4.9 Wireless Discovery Groups

Synopsis:

- Wireless environment discovery and AP/advertising control helpers.

Commands:

- `wifi scan`
- `wifi ap <on|off|status> [ssid] [password] [channel]`
- `ble scan [timeout_sec]`
- `ble advertise <on|off> [name]`
- `ble addr`
- `wardriving scan [ble_timeout_sec]`

Parameters:

- `channel`: Wi-Fi channel number.
- `timeout_sec`: BLE scan duration.
- `name`: optional BLE advertised name.

Output:

- Network/device tables and state confirmations.

Errors:

- Unsupported wireless module availability in test/host contexts.
- Invalid channel/password/time values.

Examples:

```text
wifi scan
wifi ap status
ble scan 5
ble advertise on Badge
wardriving scan 5
```

See Also:

- `net nodes`
- `radio rssi`

## 4.10 App, Config, and Misc Groups

Synopsis:

- Runtime control and utility groups for app lifecycle, config, crypto, power, and HID workflows.

Commands:

- Loader: `loader list`, `loader open <name>`, `loader close`, `loader info`
- Config: `config list`, `config get <key>`, `config set <key> <value>`, `config save`
- Crypto: `crypto has_key`, `crypto sign <message>`, `crypto verify <message> <signature>`
- Power: `power off`, `power reboot`
- BadUSB: `badusb run <path>`, `badusb type <text>`, `badusb press <key>`

Parameters:

- Group-specific; use `<group> ?` for canonical syntax on your build.

Output:

- Status lines and operation confirmations.

Errors:

- Missing app/service dependencies.
- Invalid key paths, signatures, or command arguments.

Examples:

```text
loader list
config get alias
config set alias badge42
crypto has_key
power reboot
badusb type hello
```

See Also:

- `help`
- `history`

## 5. Operational Playbooks

### 5.0 Reading Logs via CLI

Use the log command to stream runtime logs.

Host setup (Windows):

```powershell
# Find COM port
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Description

# Connect using PuTTY at 115200, then run commands below in the CLI
```

Host setup (Linux):

```bash
ls /dev/serial/by-id/
screen /dev/serial/by-id/<device-id> 115200
```

Host setup (macOS):

```bash
ls /dev/cu.*
screen /dev/cu.usbmodemXXXX 115200
```

```text
log
log error
log warn
log info
log debug
log trace
```

Behavior:

- `log` starts streaming at current level.
- Higher verbosity levels (`debug`, `trace`) can impact performance.
- Stop logging with `Ctrl+C`.

### 5.1 Chatting with Other Badges

You can chat over the active LoRa channel if all participants are on compatible settings.

Workflow:

1. Verify slot or frequency alignment.
2. Enter chat mode.
3. Send messages.
4. Exit with `Ctrl+C` when streaming mode is used.

Host setup commands (all OS):

- Open serial connection as shown in Section 2.4.
- Once connected, run the chat commands below.

Examples:

```text
lora freq 9
chat status
chat send Hello mesh
chat history
```

Or use the lora chat wrapper:

```text
lora chat 9
```

### 5.2 Health and RF Baseline

Host setup commands:

- Connect to FCLI using one of the platform methods in Section 2.4.
- Run the baseline commands below.

```text
neofetch
free
lora info
radio rssi
net address
```

Expected outcome:

- Valid system output
- No command errors
- Stable RSSI readings for idle environment

### 5.3 Capture and Replay Validation

Host setup commands:

- Connect to FCLI using one of the platform methods in Section 2.4.
- Ensure legal frequency and TX settings for your region before replay.

```text
subghz record 433.92 10 capture.sub
storage stat capture.sub
subghz replay capture.sub
```

Expected outcome:

- Capture file exists and is non-zero
- Replay reports sent packet count

### 5.4 Serial File Exchange

Receiver side:

```text
storage xreceive /payload.bin
```

Host sender examples:

Windows:

- Use PuTTY, Tera Term, or another terminal with XMODEM-CRC send support.

Linux:

- Use minicom or a terminal that supports XMODEM-CRC transfer.

macOS:

- Use minicom or another terminal with XMODEM-CRC transfer support.

Sender side:

- Start XMODEM-CRC transfer from terminal application.

Validation:

```text
storage stat /payload.bin
storage md5 /payload.bin
```

## 6. Security, Safety, and Compliance

- Operate TX only in legal bands and legal power for your location.
- Assume all payloads are observable by nearby receivers.
- Do not run disruptive scan/transmit loops in crowded RF environments.
- Avoid transmitting sensitive credentials in plain text commands.

## 7. Troubleshooting Reference

| Symptom | Likely Cause | Recommended Action |
|---|---|---|
| No prompt appears | Wrong serial settings or stale terminal | Verify COM port, 115200 baud, reconnect USB, press Enter |
| Unknown command | Typo or module not present | Run `help`, then `<group> ?`, verify firmware build |
| Streaming command does not stop | Interrupt not sent | Send `Ctrl+C`, then Enter |
| Replay command errors | Missing file or bad format | Check `storage list`, `storage stat`, recreate capture |
| File transfer fails | Protocol mismatch | Use XMODEM-CRC mode both ends |

## 8. Testing and Validation

From firmware directory:

```bash
python -m pytest tests/test_commands.py tests/test_shell.py tests/test_signal_recorder.py -v
```

For multi-device and hardware-in-the-loop scenarios, run HITL tests in tests directory with the appropriate serial-port arguments.

## 9. Implementation Pointers for Contributors

- Command modules: badge/badge_cli/commands
- Shell dispatcher: badge/badge_cli/shell.py
- Sub-GHz capture helpers: badge/radio

When adding a new command group:

1. Create a new command module.
2. Register group and subcommands in module initializer.
3. Wire module into shell command initialization.
4. Add tests to tests/test_commands.py or a dedicated test file.
