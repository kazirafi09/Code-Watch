import hashlib
def check(pw: str, expected: str) -> bool:
    return hashlib.sha1(pw.encode()).hexdigest() == expected
