"""Helper logic for dealing with signed messages"""

from cryptography import hashes, padding, serialization

class Crypto:

    def __init__(self, key_name=None):
        key_name = key_name or "supercon"
        with open(f"/data/{key_name}_public.der", "rb") as public_key_file:
            self.public_key = serialization.load_der_public_key(public_key_file.read())
        try:
            with open(f"/data/{key_name}_private.der", "rb") as private_key_file:
                self.private_key = serialization.load_der_private_key(private_key_file.read(), None)
            if not self.verify("key self check", self.sign("key self check")):
                self.private_key = None
        except OSError:
            # print("No private key on this badge, unable to cryptographically sign")
            self.private_key = None

    def sign(self, message):
        if self.private_key is None:
            raise ValueError("No private key on this badge, unable to cryptographically sign.")
        signature = self.private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), 
                        salt_length=hashes.SHA256().digest_size),
            hashes.SHA256()
        )
        return signature

    def verify(self, message, signature):
        try:
            self.public_key.verify(
                signature,
                message,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), 
                            salt_length=hashes.SHA256().digest_size),
                hashes.SHA256()
            )
            return True
        except:
            return False
