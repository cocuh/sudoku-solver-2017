import argparse
from collections import Counter, namedtuple
from concurrent.futures import Executor, TimeoutError, Future, ProcessPoolExecutor, thread
import copy
import logging
import math
import os
import random
import sys
import time
from typing import List, Optional, Set, Tuple, Dict, TextIO

logger = logging.getLogger(__name__)
NUM_WORKER = os.cpu_count() * 2


class SudokuConflict(BaseException):
  pass


class PropagateBlockNameQueue(Counter):
  '''Briefly, priority queue
  
  This queue counts the propagation to block as priority.
  The the priority is high, many cells try to propagate their conditions to the block.
  '''

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
  typename='InnerBlockPropagateResult',
  field_names=['has_cell_assigned', 'update_req_cells'],
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
    '''propagate block status to cells, and update the cell's possibilities.
    '''
    result = None

    update_req_cells: Set[Cell] = set()
    while result is None or result.has_cell_assigned:
      result = self._propagate(sudoku)
      update_req_cells.update(result.update_req_cells)

    update_req_block_name_counter = Counter()

    for c in update_req_cells:  # type:Cell
      update_req_block_name_counter.update(c.block_names)
    return update_req_block_name_counter

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
    has_cell_assigned = False

    # initialize possibles_counter and update cell's possible
    for c in filter(lambda c: not c.is_assigned(), cells):
      if c.possibles - self.rest_values:
        # the cell is required to update
        c.possibles = c.possibles.intersection(self.rest_values)
        update_req_cells.add(c)
      possibles_counter.update(c.possibles)

    # identifiable cell value's because of all different constraint
    one_possibles = {
      k
      for k, v in possibles_counter.items()
      if v == 1
    }

    for c in filter(lambda c: not c.is_assigned(), cells):
      the_one_possibles = one_possibles.intersection(c.possibles)
      if the_one_possibles:  # the cell is identifiable by all different constraint 
        if len(the_one_possibles) == 1:
          value = list(the_one_possibles)[0]
          c.assign(value)
          update_req_cells.add(c)
          has_cell_assigned = True
        else:
          raise SudokuConflict('multiple inferred values in one cell')
      elif len(c.possibles) == 1:  # possible values of the cell is singleton 
        value = list(c.possibles)[0]
        c.assign(value)
        update_req_cells.add(c)
        has_cell_assigned = True
    return InnerBlockPropagateResult(
      has_cell_assigned=has_cell_assigned,
      update_req_cells=update_req_cells,
    )

  def __repr__(self):
    return '<Block rest_values={}>'.format(sorted([i for i in self.rest_values]))


class SudokuResult:
  '''The result form of sudoku.
  '''
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
  propagate_block_name_queue: PropagateBlockNameQueue
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
    self.propagate_block_name_queue = PropagateBlockNameQueue()

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
    self.propagate_block_name_queue.update(cell.block_names)

  def propagate(self):
    while not self.propagate_block_name_queue.empty():
      block_name, count = self.propagate_block_name_queue.dequeue()
      block = self.get_block(block_name)
      propagate_req_blocks = block.propagate(self)
      self.propagate_block_name_queue.update(propagate_req_blocks)

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

  def sample_cell_for_assuming(self, sudoku) -> Cell:
    return min(
      (c for c in self.cells.values() if c.value is None),
      key=lambda c: (
        len(c.possibles),
        sum(len(b.rest_values) for b in map(sudoku.get_block, c.block_names))
      ),
    )

  def __str__(self):
    return str(self.gen_result())


MultiProcessedWorkerResult = namedtuple(
  'MultiProcessedWorkerResult',
  ['sudoku_results', 'assumptions'],
)


def _solve_worker_multi(sudoku: Sudoku, one_solution: bool) -> MultiProcessedWorkerResult:
  sudoku.propagate()
  result = None
  assumptions = []
  if sudoku.is_all_assigned():
    result = [sudoku.gen_result()]
  else:
    target_cell: Cell = sudoku.sample_cell_for_assuming(sudoku)
    values = copy.deepcopy(target_cell.possibles)
    target_cell_coord = copy.deepcopy(target_cell.coord)
    assumptions = []
    for value in values:
      sudoku_child = copy.deepcopy(sudoku)
      sudoku_child.assign(target_cell_coord, value)
      assumptions.append(sudoku_child)
  return MultiProcessedWorkerResult(sudoku_results=result, assumptions=assumptions)


def _solve_worker_single(sudoku: Sudoku, one_solution) -> MultiProcessedWorkerResult:
  results = _solve_single_thread(sudoku, one_solution)
  return MultiProcessedWorkerResult(
    sudoku_results=results,
    assumptions=[],
  )


def _solve_single_thread(sudoku: Sudoku, one_solution: bool) -> List[SudokuResult]:
  sudoku.propagate()
  if sudoku.is_all_assigned():
    return [sudoku.gen_result()]

  results = []

  target_cell: Cell = sudoku.sample_cell_for_assuming(sudoku)
  values = copy.deepcopy(target_cell.possibles)
  target_cell_coord = copy.deepcopy(target_cell.coord)

  for sudoku_child, value in [(copy.deepcopy(sudoku), v) for v in values]:
    sudoku_child.assign(target_cell_coord, value)
    try:
      child_results = _solve_single_thread(sudoku_child, one_solution)
      results += child_results
      if child_results:
        logger.debug('find satisfied result:{}'.format(len(results)))
      if one_solution and child_results:
        return results
    except SudokuConflict:
      pass
  return results


def solve(sudoku: Sudoku,
          executor: Optional[Executor],
          one_solution: bool) -> List[SudokuResult]:
  if executor is None:
    # single thread
    logger.debug('single threading')
    return _solve_single_thread(sudoku, one_solution)
  else:
    # multi-threading/processing 
    logger.debug('multi-threading/processing')

    satisfied_results = []

    futures = [executor.submit(_solve_worker_multi, sudoku, one_solution)]
    while futures:  # type: List[Future]
      if one_solution:
        f = futures.pop()  # type:Future
      else:
        idx = random.randint(0, int(min(NUM_WORKER, len(futures) - 1)))
        f = futures.pop(idx)  # type:Future
      try:
        result: MultiProcessedWorkerResult = f.result(timeout=0.1)
        if result.sudoku_results:
          satisfied_results += result.sudoku_results
          if one_solution:
            executor.shutdown(False)
            for f in futures:  # type:Future
              f.cancel()
            return satisfied_results
        else:
          for idx, sudoku_child in enumerate(result.assumptions):
            if len(futures) <= NUM_WORKER * 2:
              logger.debug('add task and gen task: #task={} #sol={}'.format(
                len(futures), len(satisfied_results)))
              futures.append(executor.submit(_solve_worker_multi, sudoku_child, one_solution))
            else:
              logger.debug('add task as to the last: #task={} #sol={}'.format(
                len(futures), len(satisfied_results)))
              futures.append(executor.submit(_solve_worker_single, sudoku_child, one_solution))
      except SudokuConflict:
        logger.debug('Sudoku Conflict in child')
      except TimeoutError:
        logger.debug('next future #task={} #sol={}'.format(
                len(futures), len(satisfied_results)))
        futures.insert(NUM_WORKER, f)
    return satisfied_results


def parse_csv(fp: TextIO) -> Sudoku:
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


def parse_args():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    'problem_csv',
    type=argparse.FileType('r'),
  )
  parser.add_argument(
    '--output',
    type=argparse.FileType('w'),
    default=sys.stdout,
  )
  parser.add_argument(
    '--parallel',
    action='store_true',
    help='solve with cpu_num*2 worker processes if specified,\n'
         'default: single threading',
  )
  parser.add_argument(
    '--debug',
    action='store_true',
  )
  parser.add_argument(
    '--one',
    action='store_true',
    help='if you want only one solution.'
  )
  return parser.parse_args()


def main():
  args = parse_args()
  if args.debug:
    logging.basicConfig(
      level=logging.DEBUG,
    )
  sudoku = parse_csv(args.problem_csv)
  output: TextIO = args.output

  start_time = time.time()
  one_solution = args.one

  if args.parallel:
    executor = ProcessPoolExecutor(NUM_WORKER)
  else:
    executor = None

  output.write(str(sudoku))
  try:
    results = solve(sudoku, executor, one_solution)
  except SudokuConflict:
    results = []
  finally:
    end_time = time.time()

  output.write('\n\n')

  if results:
    if len(results) == 1 and not one_solution:
      output.write('SATISFIABLE: well-posed problem\n')
    else:
      output.write('SATISFIABLE\n')
    output.write('#solutions = {}\n'.format(len(results)))
    output.write('spend time(sec) = {}\n'.format(end_time - start_time))
    output.write('\n')
    for idx, res in enumerate(results, start=1):
      output.write('solution {}/{}\n'.format(idx, len(results)))
      output.write(str(res))
      output.write('\n\n')
    output.write('#solutions = {}\n'.format(len(results)))
    output.write('spend time(sec) = {}\n'.format(end_time - start_time))
  else:
    output.write('UNSATISFIABLE\n')
  sys.exit()


if __name__ == '__main__':
  main()
