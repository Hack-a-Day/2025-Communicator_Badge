"""Storage commands: storage list, read, write, stat, md5, mkdir, remove."""

import os


class StorageCommands:
    """Registers the 'storage' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "storage",
            {
                "list": (self._cmd_list, "List directory: storage list [path]"),
                "read": (self._cmd_read, "Print file contents: storage read <path>"),
                "write": (self._cmd_write, "Write text to file (overwrites): storage write <path> <data...>"),
                "append": (self._cmd_append, "Append text to file: storage append <path> <data...>"),
                "stat": (self._cmd_stat, "File/dir info: storage stat <path>"),
                "md5": (self._cmd_md5, "MD5 hash: storage md5 <path>"),
                "mkdir": (self._cmd_mkdir, "Create directory: storage mkdir <path>"),
                "remove": (self._cmd_remove, "Delete file/dir: storage remove <path>"),
                "pull": (self._cmd_pull, "Download file as base64: storage pull <path>"),
                "push": (self._cmd_push, "Upload file from base64: storage push <path> <b64_data>"),
                "xsend": (self._cmd_xsend, "Send a file via XMODEM-CRC: storage xsend <path>"),
                "xreceive": (self._cmd_xreceive, "Receive a file via XMODEM-CRC: storage xreceive <path>"),
            },
            "Flash filesystem operations"
        )

    def _cmd_list(self, args):
        """List directory contents."""
        w = self.shell._write
        path = args[0] if args else "/"
        try:
            entries = os.listdir(path)
            entries.sort()
            for entry in entries:
                full_path = path.rstrip("/") + "/" + entry
                try:
                    stat = os.stat(full_path)
                    is_dir = stat[0] & 0x4000
                    size = stat[6]
                    if is_dir:
                        w("  [DIR]  " + entry + "/")
                    else:
                        w("  %6d  %s" % (size, entry))
                except OSError:
                    w("  ?      " + entry)
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_read(self, args):
        """Print file contents to serial."""
        w = self.shell._write
        if not args:
            w("Usage: storage read <path>")
            return
        path = args[0]
        try:
            with open(path, "r") as f:
                for line in f:
                    w(line.rstrip("\r\n"))
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_write(self, args):
        """Write data to a file.

        Usage: storage write <path> <data...>
        All remaining arguments are joined and written.
        """
        w = self.shell._write
        if len(args) < 2:
            w("Usage: storage write <path> <data...>")
            return
        path = args[0]
        data = " ".join(args[1:])
        try:
            with open(path, "w") as f:
                f.write(data)
            w("Wrote %d bytes to %s" % (len(data), path))
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_append(self, args):
        """Append data to a file."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: storage append <path> <data...>")
            return
        path = args[0]
        data = " ".join(args[1:])
        try:
            with open(path, "a") as f:
                f.write(data + "\n")
            w("Appended %d bytes to %s" % (len(data), path))
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_stat(self, args):
        """Show file/directory info."""
        w = self.shell._write
        if not args:
            w("Usage: storage stat <path>")
            return
        path = args[0]
        try:
            stat = os.stat(path)
            is_dir = stat[0] & 0x4000
            w("Path:  " + path)
            w("Type:  " + ("directory" if is_dir else "file"))
            w("Size:  %d bytes" % stat[6])
            w("Mode:  0x%04x" % stat[0])
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_md5(self, args):
        """Compute MD5 hash of a file."""
        w = self.shell._write
        if not args:
            w("Usage: storage md5 <path>")
            return
        path = args[0]
        try:
            import hashlib
            h = hashlib.md5()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    h.update(chunk)
            w("MD5: " + h.hexdigest() + "  " + path)
        except ImportError:
            w("hashlib.md5 not available on this platform")
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_mkdir(self, args):
        """Create a directory."""
        w = self.shell._write
        if not args:
            w("Usage: storage mkdir <path>")
            return
        try:
            os.mkdir(args[0])
            w("Created: " + args[0])
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_remove(self, args):
        """Remove a file or empty directory."""
        w = self.shell._write
        if not args:
            w("Usage: storage remove <path>")
            return
        path = args[0]
        try:
            stat = os.stat(path)
            is_dir = stat[0] & 0x4000
            if is_dir:
                os.rmdir(path)
            else:
                os.remove(path)
            w("Removed: " + path)
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_pull(self, args):
        """Download file as base64 to serial terminal."""
        w = self.shell._write
        if not args:
            w("Usage: storage pull <path>")
            return
        path = args[0]
        try:
            try:
                import ubinascii as binascii
            except ImportError:
                import binascii
            
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(45) # 45 bytes encodes cleanly to 60 base64 chars
                    if not chunk:
                        break
                    w(binascii.b2a_base64(chunk).decode('ascii').strip())
            w("") # Add newline at end
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_push(self, args):
        """Upload file from base64 data.
        
        Usage: storage push <path> <b64_data>
        """
        w = self.shell._write
        if len(args) < 2:
            w("Usage: storage push <path> <b64_data>")
            return
        path = args[0]
        b64_data = "".join(args[1:])
        try:
            try:
                import ubinascii as binascii
            except ImportError:
                import binascii
                
            raw_data = binascii.a2b_base64(b64_data)
            with open(path, "wb") as f:
                f.write(raw_data)
            w("Wrote %d bytes to %s" % (len(raw_data), path))
        except Exception as e:
            w("Error: " + str(e))

    # ── XMODEM Implementation ──────────────────────────────────────────

    SOH = b"\x01"
    EOT = b"\x04"
    ACK = b"\x06"
    NAK = b"\x15"
    CAN = b"\x18"
    CRC_CHAR = b"C"

    def _crc16(self, data):
        """CRC-16-CCITT (XMODEM variant)."""
        try:
            import binascii
            return binascii.crc_hqx(data, 0)
        except:
            # Slow fallback for environments without binascii.crc_hqx
            crc = 0
            for byte in data:
                crc = crc ^ (byte << 8)
                for _ in range(8):
                    if crc & 0x8000:
                        crc = (crc << 1) ^ 0x1021
                    else:
                        crc = crc << 1
                    crc &= 0xFFFF
            return crc

    def _cmd_xreceive(self, args):
        """Receive a file via XMODEM-CRC."""
        if not args:
            self.shell._write("Usage: storage xreceive <path>")
            return
        path = args[0]

        try:
            f = open(path, "wb")
        except Exception as e:
            self.shell._write("Error: " + str(e))
            return

        self.shell._write("Starting XMODEM-CRC receive. Start sender now...")
        
        expected_pkt = 1
        errors = 0
        max_errors = 10
        
        try:
            # Initial handshaking: send 'C' every 3 seconds
            for _ in range(10):
                self.shell._write_raw(self.CRC_CHAR)
                b = self.shell._read_byte(3000)
                if b in (self.SOH, self.EOT, self.CAN):
                    break
            else:
                self.shell._write("Timeout waiting for sender.")
                f.close()
                return

            while True:
                if b == self.SOH:
                    # Read packet: pkt#, ~pkt#, 128 bytes, 2 bytes CRC
                    header = self.shell._read_raw(2)
                    if len(header) < 2:
                        self.shell._write_raw(self.NAK)
                        b = self.shell._read_byte(1000)
                        continue
                    
                    pkt_num = header[0]
                    pkt_inv = header[1]
                    
                    data = self.shell._read_raw(128)
                    crc_bytes = self.shell._read_raw(2)
                    
                    if len(data) < 128 or len(crc_bytes) < 2:
                        self.shell._write_raw(self.NAK)
                        b = self.shell._read_byte(1000)
                        continue

                    # Verify
                    actual_crc = self._crc16(data)
                    expected_crc = (crc_bytes[0] << 8) | crc_bytes[1]
                    
                    if pkt_num == (expected_pkt & 0xFF) and (pkt_num + pkt_inv) == 0xFF and actual_crc == expected_crc:
                        f.write(data)
                        self.shell._write_raw(self.ACK)
                        expected_pkt += 1
                        errors = 0
                    elif pkt_num == ((expected_pkt - 1) & 0xFF):
                        # Duplicate packet (sender didn't get ACK)
                        self.shell._write_raw(self.ACK)
                    else:
                        self.shell._write_raw(self.NAK)
                        errors += 1
                    
                elif b == self.EOT:
                    self.shell._write_raw(self.ACK)
                    self.shell._write("\r\nTransfer complete.")
                    break
                elif b == self.CAN:
                    self.shell._write("\r\nTransfer cancelled by sender.")
                    break
                else:
                    errors += 1
                    if errors > max_errors:
                        self.shell._write_raw(self.CAN)
                        self.shell._write("\r\nToo many errors, aborting.")
                        break
                    self.shell._write_raw(self.NAK)
                
                if errors > max_errors: break
                b = self.shell._read_byte(3000)
                if b is None:
                    self.shell._write("\r\nTimeout waiting for packet.")
                    break

        finally:
            f.close()

    def _cmd_xsend(self, args):
        """Send a file via XMODEM-CRC."""
        if not args:
            self.shell._write("Usage: storage xsend <path>")
            return
        path = args[0]

        try:
            f = open(path, "rb")
        except Exception as e:
            self.shell._write("Error: " + str(e))
            return

        self.shell._write("Waiting for receiver to send 'C'...")
        
        try:
            # Wait for 'C'
            while True:
                b = self.shell._read_byte(1000)
                if b == self.CRC_CHAR:
                    break
                if b == self.CAN:
                    self.shell._write("Cancelled by receiver.")
                    return
            
            pkt_num = 1
            while True:
                data = f.read(128)
                if not data:
                    break
                
                # Pad data to 128 bytes
                if len(data) < 128:
                    data += b"\x1a" * (128 - len(data)) # EOF char padding
                
                pkt = self.SOH + bytes([pkt_num & 0xFF, (0xFF - (pkt_num & 0xFF))])
                pkt += data
                crc = self._crc16(data)
                pkt += bytes([(crc >> 8) & 0xFF, crc & 0xFF])
                
                # Send and wait for ACK
                attempts = 0
                while attempts < 10:
                    self.shell._write_raw(pkt)
                    resp = self.shell._read_byte(3000)
                    if resp == self.ACK:
                        pkt_num += 1
                        break
                    attempts += 1
                else:
                    self.shell._write("Failed to send packet after 10 attempts.")
                    return

            # Send EOT
            attempts = 0
            while attempts < 10:
                self.shell._write_raw(self.EOT)
                resp = self.shell._read_byte(3000)
                if resp == self.ACK:
                    self.shell._write("Transfer complete.")
                    break
                attempts += 1
                
        finally:
            f.close()
