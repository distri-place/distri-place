from collections.abc import Callable


class Canvas:
    def __init__(self, size: int = 64, on_update: Callable[[int, int, int], None] | None = None):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]
        self.on_update = on_update

    def update(self, x: int, y: int, color: int):
        self.grid[y][x] = color
        if self.on_update:
            self.on_update(x, y, color)

    def get_all_pixels(self) -> list[int]:
        return [pixel for row in self.grid for pixel in row]
