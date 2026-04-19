"""Mock Crypto for testing without ucryptography hardware."""


class MockCrypto:
    """Fake Crypto that always succeeds for sign/verify.

    In tests, sign() returns a fixed signature and verify() always
    returns True. This allows testing CLI commands that use crypto
    without needing RSA keys.
    """

    def __init__(self, has_private_key=False):
        self.public_key = b"mock_public_key"
        self.private_key = b"mock_private_key" if has_private_key else None
        self._sign_log = []
        self._verify_log = []

    def sign(self, message):
        if self.private_key is None:
            raise ValueError("No private key on this badge, unable to cryptographically sign.")
        if isinstance(message, str):
            message = message.encode()
        self._sign_log.append(message)
        return b"mock_signature_" + message[:16]

    def verify(self, message, signature):
        if isinstance(message, str):
            message = message.encode()
        self._verify_log.append((message, signature))
        # Accept any mock signature
        return signature.startswith(b"mock_signature_")
