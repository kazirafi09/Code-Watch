from dataclasses import dataclass
@dataclass
class Point:
    x: float
    y: float
    def norm(self) -> float:
        return (self.x * self.x + self.y * self.y) ** 0.5
