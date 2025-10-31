"""Manages mutable data file on the badge. Allows storing data in a dictionary of {bytes:bytes}"""

import os

# btree exists in micropython but not cpython.
# For IDE purposes, fake out the btree object returned by btree.open().
try:
    import btree  # type: ignore
except ImportError:

    class _BTree(dict):
        def flush(self):
            pass

        def close(self):
            pass

    btree = None


class DataFile:
    """Base class for files stored by the OS or apps."""

    def __init__(self, name: str):
        self.name = name
        self.path = "/data/" + name
        if "data" not in os.listdir("/"):
            os.mkdir("/data")
        try:
            self.file = open(self.path, "r+b")
        except OSError:
            self.file = open(self.path, "w+b")
        if btree:
            self.db = btree.open(self.file)
        else:
            self.db = _BTree()

    def flush(self):
        if btree:
            self.db.flush()

    def set(self, name: str, value: str | bytes) -> None:
        if not isinstance(value, (str, bytes)):
            raise ValueError(
                f"Error: {self.name} can only store keys of `str` or `bytes`. {name}={value} is {type(value)}."
            )
        self.db[name] = value

    def get(self, key: str, default: bytes | None = None) -> bytes | None:
        return self.db.get(key, default)

    def close(self):
        self.db.close()
        self.file.close()


class Config(DataFile):
    """Store static config for this badge.
    Managed by config_manager.ConfigManager.
    Config keys:
        address: Set automatically, should not be modified
        alias: My nickname (max 16 characters)
    """

    def __init__(self):
        super().__init__("config")
