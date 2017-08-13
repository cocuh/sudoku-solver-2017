from typing import List, Optional, Set, Tuple, Dict
from weakref import ref
from collections import Counter, namedtuple

import copy
import math
import sys

import time


class SudokuConflict(BaseException):
  pass


class CounterQueue(Counter):
  def dequeue(self):
    result_opt = self.most_common(1)
    if result_opt == []:
      return None
    else:
      key, count = result_opt[0]
      self.pop(key)
      return key, count

  def empty(self) -> bool:
    return len(self.keys()) == 0


class Cell:
  coord: Tuple[int, int]
  possibles: Set[int]
  value: Optional[int]
  block_names: List[str]

  def __init__(self, coord: Tuple[int, int], degree: int):
    self.coord = coord
    num = degree ** 2
    self.possibles = set(range(1, num + 1))
    self.block_names = []
    self.value = None

  def register_block(self, block_name: str):
    self.block_names.append(block_name)

  def assign(self, value):
    self.possibles = {value}
    self.value = value

  def is_assigned(self):
    return self.value is not None

  @property
  def x(self):
    return self.coord[0]

  @property
  def y(self):
    return self.coord[1]


InnerBlockPropagateResult = namedtuple(
  typename='InnerBlockInferenceResult',
  field_names=['has_assigned', 'update_req_cells'],
)


class Block:
  cells: List[Tuple[int, int]]
  degree: int
  rest_values: Set[int]
  name: str

  def __init__(self, name: str, cells: List[Tuple[int, int]], degree: int):
    num = degree ** 2
    assert len(cells) == num
    self.name = name
    self.cells = cells
    self.degree = degree
    self.rest_values = set(range(1, num + 1))

  def propagate(self, sudoku: 'Sudoku') -> Dict[str, int]:
    result = self._propagate(sudoku)
    update_req_cells = set(result.update_req_cells)
    while result.has_assigned:
      result = self._propagate(sudoku)
      update_req_cells.update(result.update_req_cells)
    counter = Counter()
    for c in update_req_cells:  # type:Cell
      counter.update(c.block_names)
    return counter

  def _propagate(self, sudoku: 'Sudoku') -> InnerBlockPropagateResult:
    cells = list(map(sudoku.get_cell, self.cells))
    assigned_values: Counter = Counter(
      c.value
        for c in cells
        if c.value is not None
    )
    if any(v != 1 for v in assigned_values.values()):
      raise SudokuConflict('double assignments in all different')

    self.rest_values: Set[int] = self.rest_values.difference(set(assigned_values.keys()))
    possibles_counter = Counter()

    update_req_cells = set()
    has_assigned = False

    # initialize possibles_counter
    for c in filter(lambda c: not c.is_assigned(), cells):
      if c.possibles - self.rest_values:
        # update required
        c.possibles = c.possibles.intersection(self.rest_values)
        update_req_cells.add(c)
      possibles_counter.update(c.possibles)

    one_possibles = {
      k
      for k, v in possibles_counter.items()
      if v == 1
    }
    for c in filter(lambda c: not c.is_assigned(), cells):
      the_one_possibles = one_possibles.intersection(c.possibles)
      if the_one_possibles:
        if len(the_one_possibles) == 1:
          value = list(the_one_possibles)[0]
          c.assign(value)
          update_req_cells.add(c)
          has_assigned = True
        else:
          raise SudokuConflict('multiple inferred values in one cell')
      elif len(c.possibles) == 1:
        value = list(c.possibles)[0]
        c.assign(value)
        update_req_cells.add(c)
        has_assigned = True
    return InnerBlockPropagateResult(
      has_assigned=has_assigned,
      update_req_cells=update_req_cells,
    )

  def __repr__(self):
    return '<Block rest_values={}>'.format(sorted([i for i in self.rest_values]))


class SudokuResult:
  cells: Dict[Tuple[int, int], Optional[int]]
  degree: int

  def __init__(self, cells, degree):
    self.cells = cells
    self.degree = degree

  def __str__(self):
    num = self.degree ** 2
    digits = num // 10 + 1
    cell_tmp = '{' + ':{}d'.format(digits) + '}'
    result = []
    for y in range(num):
      result_line = []
      for x in range(num):
        value = self.cells[(x, y)]
        if value is None:
          cell_str = ' ' * digits
        else:
          cell_str = cell_tmp.format(value)
        result_line.append(cell_str)

        if x + 1 == num:
          pass
        elif (x + 1) % self.degree == 0:
          result_line.append('|')
        else:
          result_line.append(',')
      result.append(''.join(result_line))
      if y + 1 == num:
        pass
      elif (y + 1) % self.degree == 0:
        result.append('-' * (digits * num + num - 1))

    return '\n'.join(result)


class Sudoku:
  cells: Dict[Tuple[int, int], Cell]
  blocks: List[Block]
  inference_block_name_queue: CounterQueue
  degree: int

  def __init__(self, degree):
    num = degree ** 2
    self.degree = degree
    cells = [
      Cell((x, y), degree)
      for x in range(num)
      for y in range(num)
    ]
    self.cells = {
      (c.x, c.y): c
      for c in cells
    }
    self.blocks = {
      b.name: b
      for b in self.gen_blocks(cells, degree)
    }
    self.inference_block_name_queue = CounterQueue()

  @staticmethod
  def gen_blocks(cells: List[Cell], degree: int) -> List[Block]:
    num = degree ** 2
    x_dic = {n: [] for n in range(num)}
    y_dic = {n: [] for n in range(num)}
    c_dic = {(x, y): [] for x in range(degree) for y in range(degree)}

    for c in cells:
      x_dic[c.x].append(c)
      y_dic[c.y].append(c)
      c_dic[(c.x // degree, c.y // degree)].append(c)

    blocks = []
    for dic, name_tmp in [
      (x_dic, 'x_{}'),
      (y_dic, 'y_{}'),
      (c_dic, 'c_{}'),
    ]:
      for key, cs in dic.items():
        name = name_tmp.format(key)
        c_coords = [c.coord for c in cs]
        b = Block(name, c_coords, degree)
        for c in cs:  # type: Cell
          c.register_block(b.name)
        blocks.append(b)
    return blocks

  def assign(self, coord: Tuple[int, int], value: int):
    cell: Cell = self.cells[coord]
    cell.assign(value)
    self.inference_block_name_queue.update(cell.block_names)

  def propagate(self):
    while not self.inference_block_name_queue.empty():
      block_name, count = self.inference_block_name_queue.dequeue()
      block = self.get_block(block_name)
      inference_req_blocks = block.propagate(self)
      self.inference_block_name_queue.update(inference_req_blocks)

  def is_all_assigned(self) -> bool:
    return all(c.value is not None for c in self.cells.values())

  def get_cell(self, c_pos: Tuple[int, int]) -> Cell:
    return self.cells[c_pos]

  def get_block(self, b_name: str) -> Block:
    return self.blocks[b_name]

  def gen_result(self):
    return SudokuResult(
      cells={
        k: v.value
        for k, v in self.cells.items()
      },
      degree=self.degree,
    )

  def sample_cell_for_assuming(self) -> Cell:
    return min(
      (c for c in self.cells.values() if c.value is None),
      key=lambda c: len(c.possibles),
    )

  def __str__(self):
    return str(self.gen_result())


def solve(sudoku: Sudoku) -> List[SudokuResult]:
  sudoku.propagate()
  if sudoku.is_all_assigned():
    return [sudoku.gen_result()]

  results = []

  target_cell: Cell = sudoku.sample_cell_for_assuming()
  values = copy.deepcopy(target_cell.possibles)
  target_cell_coord = copy.deepcopy(target_cell.coord)

  for sudoku_child, value in [(copy.deepcopy(sudoku), v) for v in values]:
    print('try assigning: {}={}'.format(target_cell_coord, value))
    sudoku_child.assign(target_cell_coord, value)
    try:
      child_results = solve(sudoku_child)
      results += child_results
    except SudokuConflict:
      print('backtrack')
      pass
  return results


def parse_csv(filepath: str) -> Sudoku:
  with open(filepath) as fp:
    body = fp.read().strip()
    lines = list(body.splitlines())
  num_lines = len(lines)
  degree = math.floor(math.sqrt(num_lines))
  if degree ** 2 < num_lines:
    degree += 1
  assert degree ** 2 == num_lines, "can't get degree"

  sudoku = Sudoku(degree)
  num = degree ** 2

  for y, line in enumerate(lines):
    for x, value in enumerate(line.split(',')):
      value = value.strip()
      if value.isnumeric():
        value = int(value)
        assert 1 <= value <= num, "invalid value, value should be 1-start"
        sudoku.assign((x, y), value)
  return sudoku


def usage():
  print('{} csv_path'.format(sys.argv[0]))


def main():
  if len(sys.argv) != 2:
    usage()
    sys.exit(1)
  filepath = sys.argv[1]
  sudoku = parse_csv(filepath)

  start_time = time.time()

  print(sudoku)
  try:
    results = solve(sudoku)
  except SudokuConflict:
    results = []
  finally:
    end_time = time.time()

  print()

  if results:
    if len(results) == 1:
      print('SATISFIABLE: well-posed problem')
    else:
      print('SATISFIABLE')
    print('#solutions = {}'.format(len(results)))
    print('spend time(sec) = {}'.format(end_time - start_time))
    print()
    for idx, res in enumerate(results, start=1):
      print('solution {}/{}'.format(idx, len(results)))
      print(res)
      print()
  else:
    print('UNSATISFIABLE')


if __name__ == '__main__':
  main()
