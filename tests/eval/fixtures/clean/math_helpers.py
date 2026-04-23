import math
def circle_area(r: float) -> float:
    return math.pi * r * r
def manhattan(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))
