"""Loader commands: loader list, open, info, close."""


class LoaderCommands:
    """Registers the 'loader' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "loader",
            {
                "list": (self._cmd_list, "List all registered apps"),
                "open": (self._cmd_open, "Bring app to foreground: loader open <name>"),
                "info": (self._cmd_info, "Show current foreground app"),
                "close": (self._cmd_close, "Send foreground app to background"),
            },
            "Application loader"
        )

    def _get_apps(self):
        try:
            from apps.base_app import BaseApp
            return BaseApp.all_apps
        except ImportError:
            return []

    def _cmd_list(self, args):
        w = self.shell._write
        apps = self._get_apps()
        if not apps:
            w("No apps registered.")
            return
        w("Registered apps:")
        for app in apps:
            if app.active_foreground:
                state = "[FG]"
            elif app.active_background:
                state = "[BG]"
            else:
                state = "[--]"
            w("  %s %-20s" % (state, app.name))

    def _cmd_open(self, args):
        w = self.shell._write
        if not args:
            w("Usage: loader open <app_name>")
            return
        name = " ".join(args)
        app = self.shell.find_app(name)
        if app is None:
            w("App not found: " + name)
            return
        try:
            app.switch_to_foreground()
            w("Opened: " + app.name)
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_info(self, args):
        w = self.shell._write
        apps = self._get_apps()
        fg_apps = [a for a in apps if a.active_foreground]
        if fg_apps:
            for app in fg_apps:
                w("Foreground: " + app.name)
        else:
            w("No foreground app.")

    def _cmd_close(self, args):
        w = self.shell._write
        apps = self._get_apps()
        fg_apps = [a for a in apps if a.active_foreground]
        if not fg_apps:
            w("No foreground app to close.")
            return
        for app in fg_apps:
            try:
                app.switch_to_background()
                w("Closed: " + app.name)
            except Exception as e:
                w("Error closing " + app.name + ": " + str(e))
