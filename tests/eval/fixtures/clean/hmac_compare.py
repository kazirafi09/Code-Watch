import hmac
def check_api_key(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided, expected)
