import queue
from typing import List, Optional, Set
from weakref import ref
from collections import Counter


class Cell:
  x: int
  y: int
  possibles: Set[int]
  value: Optional[int]
  blocks: List[ref]

  def __init__(self, x, y, degree):
    self.x = x
    self.y = y
    num = degree ** 2
    self.possibles = set(range(num))
    self.blocks = []
    self.value = None

  def register_block(self, block: 'Block'):
    self.blocks.append(ref(block))

  def assign(self, value):
    self.possibles = {value}
    self.value = value


class Block:
  cells: List[Cell]
  degree: int
  rest_values: Set[int]

  def __init__(self, cells: List[Cell], degree: int):
    num = degree ** 2
    assert len(cells) == num
    self.cells = cells
    self.degree = degree
    self.rest_values = set(range(num))

    for c in cells:
      c.register_block(self)

  def inferene(self):
    num = self.degree ** 2
    assigned_values: Set[int] = {}
    possibles_counter = Counter()
    for c in self.cells:
      if c.value is None:
        possibles_counter.update(c.possibles)
      else:
        assigned_values.add(c.value)

    possibles = set(possibles_counter.keys()) - assigned_values

    for c in self.cells:
      if c.value is None:
        c.possibles = c.possibles.intersection(possibles)
        if len(c.possibles) == 1:
          
      else:
        pass


class Sudoku:
  cells: List[Cell]
  blocks: List[Block]
  inference_queue: queue.Queue

  def __init__(self, degree):
    num = degree ** 2
    self.cells = [
      Cell(x, y, degree)
      for x in range(num)
      for y in range(num)
    ]
    self.pos2cell = {
      (c.x, c.y): c
      for c in self.cells
    }
    self.blocks = self.gen_blocks(self.cells, degree)
    self.inference_queue = queue.Queue()

  @staticmethod
  def gen_blocks(cells: List[Cell], degree: int):
    num = degree ** 2
    x_dic = {n: [] for n in range(num)}
    y_dic = {n: [] for n in range(num)}
    c_dic = {(x, y): [] for x in range(degree) for y in range(degree)}

    for c in cells:
      x_dic[c.x].append(c)
      y_dic[c.y].append(c)
      c_dic[(c.x // degree, c.y // degree)].append(c)

    blocks = []
    for v in x_dic.values():
      blocks.append(Block(v, degree))
    for v in y_dic.values():
      blocks.append(Block(v, degree))
    for v in c_dic.values():
      blocks.append(Block(v, degree))
    return blocks

  def assign(self, x, y, value):
    cell: Cell = self.pos2cell[(x, y)]
    cell.assign(value)
    self.inference_queue.put(cell)

  def solve(self):
    while not self.inference_queue.empty():
      cell = self.inference_queue.get()
      cell.inference()


def main():
  s = Sudoku(3)
  print(s)


if __name__ == '__main__':
  main()
