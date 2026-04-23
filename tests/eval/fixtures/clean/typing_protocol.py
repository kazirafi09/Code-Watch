from typing import Protocol
class Named(Protocol):
    name: str
def greet(obj: Named) -> str:
    return f"hi {obj.name}"
