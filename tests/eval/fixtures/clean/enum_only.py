from enum import Enum
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
def is_primary(c: Color) -> bool:
    return c in {Color.RED, Color.GREEN, Color.BLUE}
