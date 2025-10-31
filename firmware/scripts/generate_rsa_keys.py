"""Generate RSA keys for autheticated messaging

This must be run on the badge!
mpremote run scripts/generate_rsa_keys.py
"""


from cryptography import hashes, rsa, padding, serialization


def sign(message, private_key):
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), 
                    salt_length=hashes.SHA256().digest_size),
        hashes.SHA256()
    )
    return signature

def verify(message, signature, public_key):
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), 
                        salt_length=hashes.SHA256().digest_size),
            hashes.SHA256()
        )
        return True
    except:
        return False


# Generate Keys
print("Generating RSA Key")
private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
public_key = private_key.public_key()

private_key_der = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)
public_key_der = public_key.public_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

print("private_key DER", private_key_der)

print("public_key DER", public_key_der)

with open("/data/rsa_private.der", "wb") as private_file:
    private_file.write(private_key_der)

with open("/data/rsa_public.der", "wb") as public_file:
    public_file.write(public_key_der)

# Test the keys

with open("/data/rsa_private.der", "rb") as privf:
    priv = serialization.load_der_private_key(privf.read(), None)

with open("/data/rsa_public.der", "rb") as pubf:
    pub = serialization.load_der_public_key(pubf.read())

plaintext = b"Supercon will be so much fun!"
signature = sign(plaintext, private_key)
print(f"Sig: {signature}, len: {len(signature)}")
print(f"Verified: {verify(plaintext, signature, pub)}")