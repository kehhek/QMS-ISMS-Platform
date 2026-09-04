import secrets
import string


def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + '!@#%^&*-_+='
    return ''.join(secrets.choice(alphabet) for _ in range(length))
