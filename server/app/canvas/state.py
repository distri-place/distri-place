class Canvas:
    def __init__(self, size: int = 100):
        self.size = size
        self.grid = [[0] * size for _ in range(size)]

    def update(self, x: int, y: int, color: int):
        self.grid[y][x] = color
