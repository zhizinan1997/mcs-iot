import hashlib
import os
import base64

def generate_mosquitto_password(password):
    # PBKDF2-SHA512 generation consistent with mosquitto_passwd
    salt = os.urandom(12)
    # iterations = 100
    hash_val = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100)
    
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hash_b64 = base64.b64encode(hash_val).decode('utf-8')
    
    # Format: $6$salt$hash
    return f"$6${salt_b64}${hash_b64}"

users = {
    "admin": "admin123",
    "worker": "worker123",
    "device_A001": "device123" # Test device
}

with open("mcs-iot/mosquitto/config/passwd", "w") as f:
    for user, pwd in users.items():
        hash_str = generate_mosquitto_password(pwd)
        f.write(f"{user}:{hash_str}\n")
    
print(f"Generated password file for {len(users)} users.")
