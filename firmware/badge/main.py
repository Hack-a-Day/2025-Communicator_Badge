import micropython
import time
import asyncio as aio  # type: ignore

try:
    from hardware.badge import Badge
    from net.net import badgenet, capture_all_packets
    from apps import app_manager, app_menu, chat, config_manager, usb_debug, nametag, talks

    # Badge CLI and related apps.
    from apps.cli_app import CliApp
    from apps.ctf_app import CTFApp
    from apps.poll_app import PollApp
    from apps.peers_app import PeersApp
    from apps.net_tools import NetTools
    from apps.badgeshark import BadgeShark
    from apps.serial_terminal import SerialTerminalApp
    from apps.shell_gui import ShellGuiApp
except Exception as ex:
    # If anything goes wrong at import time, wait a second and print it
    # Sometimes these are hard to see, so the delay and extra print may help
    import sys
    import time

    time.sleep(1)
    sys.print_exception(ex)
    raise


async def main():
    print("Initializing main...")
    badge = Badge()
    badgenet.init(badge)
    user_app_manager = app_manager.AppManager("Apps", badge)
    # These apps are on the main screen when the badge boots
    primary_apps = [
        chat.ChatApp("Chat", badge),
        talks.Talks("Talks", badge),
        nametag.App("Nametag", badge),
        SerialTerminalApp("Terminal", badge),
        ShellGuiApp("Shell", badge),
        user_app_manager,
        config_manager.ConfigManager("Config", badge),
    ]
    # Background apps — CLI replaces UsbDebug as the serial handler
    backgrounded_apps = [
        CliApp("CLI", badge),
        NetTools("Net Tools", badge),
        BadgeShark("BadgeShark", badge),
        CTFApp("CTF", badge),
        PollApp("Polls", badge),
        PeersApp("Peers", badge),
    ]
    main_menu = app_menu.AppMenu("Main", badge, primary_apps, True)
    for app in primary_apps:
        if app:
            app.start()
    for app in backgrounded_apps:
        app.start()
    main_menu.start()
    main_menu.switch_to_foreground()

    # To capture all network packets for debugging, set to True
    capture_all_packets(False)
    print("Badge is up and running!")
    print("Badge CLI is active on USB serial. Type 'help' for commands.")

    while True:
        await aio.sleep(60)
        print("Main 60s heartbeat --^v--^v--")
        micropython.mem_info()


if __name__ == "__main__":
    aio.run(main())

