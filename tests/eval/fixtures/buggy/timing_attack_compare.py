def check_api_key(provided: str, expected: str) -> bool:
    return provided == expected  # not constant time
