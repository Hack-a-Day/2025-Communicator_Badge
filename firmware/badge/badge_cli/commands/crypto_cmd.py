"""Crypto commands: crypto has_key, sign, verify."""


class CryptoCommands:
    """Registers the 'crypto' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "crypto",
            {
                "has_key": (self._cmd_has_key, "Check if private key is present"),
                "sign": (self._cmd_sign, "Sign a message: crypto sign <text>"),
                "verify": (self._cmd_verify, "Verify signature: crypto verify <text> <sig_hex>"),
            },
            "RSA cryptographic operations"
        )

    def _cmd_has_key(self, args):
        w = self.shell._write
        has_key = self.badge.crypto.private_key is not None
        w("Private key: " + ("present" if has_key else "not present"))
        w("Public key:  present")

    def _cmd_sign(self, args):
        w = self.shell._write
        if not args:
            w("Usage: crypto sign <message_text>")
            return

        message = " ".join(args)
        try:
            sig = self.badge.crypto.sign(message)
            w("Message:   " + message)
            w("Signature: " + sig.hex())
        except ValueError as e:
            w("Error: " + str(e))

    def _cmd_verify(self, args):
        w = self.shell._write
        if len(args) < 2:
            w("Usage: crypto verify <message_text> <signature_hex>")
            return

        sig_hex = args[-1]
        message = " ".join(args[:-1])

        try:
            sig_bytes = bytes.fromhex(sig_hex)
        except ValueError:
            w("Error: Invalid hex signature")
            return

        result = self.badge.crypto.verify(message, sig_bytes)
        w("Message:   " + message)
        w("Signature: " + sig_hex)
        w("Valid:     " + str(result))
