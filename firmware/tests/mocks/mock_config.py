"""Mock Config for testing without btree/flash hardware."""


class MockConfig:
    """Fake Config that uses an in-memory dict instead of btree on flash.

    Matches the interface of hardware.datafile.Config.
    """

    def __init__(self):
        self.db = MockBTree()
        # Set defaults matching real badge config
        self.db[b"alias"] = b""
        self.db[b"nametag"] = b"Test Badge"
        self.db[b"nametag_show_image"] = b"false"
        self.db[b"nametag_image"] = b"images/headshots/wrencher.png"
        self.db[b"radio_tx_power"] = b"9"
        self.db[b"chat_ttl"] = b"3"
        self.db[b"send_cooldown_ms"] = b"1"

    def set(self, name, value):
        if isinstance(value, str):
            value = value.encode()
        if isinstance(name, str):
            name = name.encode()
        self.db[name] = value

    def get(self, key, default=None):
        if isinstance(key, str):
            key = key.encode()
        return self.db.get(key, default)

    def flush(self):
        """No-op — nothing to flush in memory."""
        pass

    def close(self):
        """No-op."""
        pass


class MockBTree(dict):
    """Dict subclass that behaves like MicroPython's btree.

    Keys and values are bytes. Supports string keys for convenience
    (auto-encodes to bytes).
    """

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = key.encode()
        if isinstance(value, str):
            value = value.encode()
        super().__setitem__(key, value)

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.encode()
        return super().__getitem__(key)

    def __contains__(self, key):
        if isinstance(key, str):
            key = key.encode()
        return super().__contains__(key)

    def get(self, key, default=None):
        if isinstance(key, str):
            key = key.encode()
        return super().get(key, default)

    def keys(self):
        return super().keys()

    def items(self):
        return super().items()

    def flush(self):
        pass

    def close(self):
        pass
