use std::rc::{Rc, Weak};
use std::cell::RefCell;
use std::collections::{HashMap, BTreeSet};
use std::hash::{Hash, Hasher};
use std::fmt::{Debug, Formatter, Error};
use std::cmp::{Ordering};
use std::iter::FromIterator;

extern crate bit_vec;
use self::bit_vec::BitVec;

#[derive(Hash, Eq, PartialEq, Clone, Debug)]
pub struct Coords {
    pub x: usize,
    pub y: usize,
}


#[derive(Debug)]
struct Cell {
    // 1 x 1 cell
    pos: Coords,
    blocks: BTreeSet<BlockWeak>,
    pub value: Option<usize>,
    pub possibles: BitVec,
}


impl Cell {
    pub fn new(pos: Coords, degree: usize) -> Cell {
        let num = degree * degree;
        Cell {
            pos: pos,
            value: None,
            blocks: BTreeSet::new(),
            possibles: BitVec::from_elem(num, true),
        }
    }

    pub fn assign(&mut self, value: usize) -> BTreeSet<BlockRef> {
        self.value = Some(value);
        self.possibles.set_all();
        self.possibles.negate();
        self.possibles.set(value, true);
        let res = self.blocks.iter().map(
            |b|BlockRef(b.0.upgrade().unwrap())
        ).collect::<BTreeSet<_>>();
        return res;
    }

    pub fn add_block(&mut self, block_weakref: BlockWeak) {
        self.blocks.insert(block_weakref);
    }
}


#[derive(Clone)]
struct CellRef(Rc<RefCell<Cell>>);

impl Debug for CellRef {
     fn fmt(&self, f: &mut Formatter) -> Result<(), Error> {
         Ok(())
     }
}

impl PartialEq for CellRef {
    fn eq(&self, other: &CellRef) -> bool {
        self.0.borrow().pos.eq(&other.0.borrow().pos)
    }
}

impl Eq for CellRef {}

impl Hash for CellRef {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.borrow().pos.hash(state)
    }
}



#[derive(Debug)]
struct Block {
    // block which contains N cells
    name: String,
    cells: Vec<CellRef>,
    assigned_values: BitVec,
    degree: usize,
}

impl Hash for Block {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.name.hash(state)
    }
}

#[derive(Clone)]
struct BlockRef(Rc<RefCell<Block>>);


impl PartialEq for BlockRef {
    fn eq(&self, other: &BlockRef) -> bool {
        self.0.borrow().name == other.0.borrow().name
    }
}

impl Eq for BlockRef {}

impl Ord for BlockRef {
    fn cmp(&self, other: &BlockRef) -> Ordering {
        self.0.borrow().name.cmp(&other.0.borrow().name)
    }
}

impl PartialOrd for BlockRef {
    fn partial_cmp(&self, other: &BlockRef) -> Option<Ordering> {
        Some(self.0.borrow().name.cmp(&other.0.borrow().name))
    }
}


impl Hash for BlockRef{
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.borrow().hash(state);
    }
}

impl Debug for BlockRef {
    fn fmt(&self, f: &mut Formatter) -> Result<(), Error> {
        self.0.fmt(f)
    }
}



#[derive(Debug, Clone)]
struct BlockWeak(Weak<RefCell<Block>>);

impl PartialEq for BlockWeak {
    fn eq(&self, other: &BlockWeak) -> bool {
        let _left = self.0.upgrade().unwrap();
        let _right = other.0.upgrade().unwrap();
        let left = _left.borrow();
        let right = _right.borrow();
        left.name == right.name
    }
}

impl Eq for BlockWeak {}

impl Ord for BlockWeak {
    fn cmp(&self, other: &BlockWeak) -> Ordering {
        let _left = self.0.upgrade().unwrap();
        let _right = other.0.upgrade().unwrap();
        let left = _left.borrow();
        let right = _right.borrow();
        left.name.cmp(&right.name)
    }
}

impl PartialOrd for BlockWeak {
    fn partial_cmp(&self, other: &BlockWeak) -> Option<Ordering> {
        let _left = self.0.upgrade().unwrap();
        let _right = other.0.upgrade().unwrap();
        let left = _left.borrow();
        let right = _right.borrow();
        Some(left.name.cmp(&right.name))
    }
}

impl Hash for BlockWeak {
    fn hash<H: Hasher>(&self, state: &mut H) {
        let b = self.0.upgrade().unwrap();
        b.borrow().hash(state);
    }
}

impl Block {
    pub fn create(name :String, mut cells: Vec<CellRef>, degree: usize) -> BlockRef {
        assert_eq!(cells.len(), degree * degree);
        let num = degree * degree;
        let block = Block {
            name: name,
            cells: cells.clone(),
            assigned_values: BitVec::from_elem(num, false),
            degree: degree,
        };
        let block_ref = Rc::new(RefCell::new(block));
        let block_weakref = BlockWeak(Rc::downgrade(&block_ref));
        for c_ref in cells.iter_mut() {
            c_ref.0.borrow_mut().add_block(block_weakref.clone());
        }
        return BlockRef(block_ref);
    }

    pub fn inference(&mut self) -> Result<BTreeSet<BlockRef>, ()> {
        let num = self.degree * self.degree;
        let mut assigned_values = BitVec::from_elem(num, false);
        let mut possibles_value = BitVec::from_elem(num, false);
        let mut possibles_one = BitVec::from_elem(num, true);

        for c_ref in self.cells.iter() {
            match c_ref.0.borrow().value {
                Some(v) => {
                    assigned_values.set(v, true);
                    possibles_one.set(v, false);
                },
                None => {
                    let mut pos = possibles_value.clone();
                    possibles_value.union(&c_ref.0.borrow().possibles);
                    pos.intersect(&c_ref.0.borrow().possibles);
                    pos.negate();
                    possibles_one.intersect(&pos);
                },
            }
        }

        self.assigned_values = assigned_values;
        let res = BTreeSet::new();

        if possibles_one.any() {
            let mut one_cells = HashMap::new();
            for c_ref in self.cells.iter() {
                let mut pos = possibles_one.clone();
                pos.intersect(&c_ref.0.borrow().possibles);
                if pos.any() {
                    for i in 1..num {
                        match pos.get(i) {
                            Some(f) => {
                                if f {
                                    one_cells.insert(c_ref.clone(), i+1);
                                }
                            },
                            None => {
                            },
                        }
                    }
                }
            }

            for (c_ref, v) in one_cells.into_iter() {
                let blocks = c_ref.0.borrow_mut().assign(v);
                res.intersection(&blocks);
            }
        }

        let update_req_blocks = BTreeSet::new();
        for c_ref in self.cells.iter() {
            if c_ref.0.borrow().possibles == self.assigned_values {
                continue
            }
            c_ref.0.borrow_mut().possibles.intersect(&self.assigned_values);
            if c_ref.0.borrow().possibles.none() {
                return Err(());
            }
            update_req_blocks.union(&c_ref.0.borrow().blocks);
        }
        let res2 = update_req_blocks.iter().map(
            |b|BlockRef(b.0.upgrade().unwrap())
        ).collect::<BTreeSet<_>>();
        res.union(&res2);
        return Ok(res);
    }


}


pub struct Sudoku {
    cells: HashMap<Coords, CellRef>,
    update_req_blocks: BTreeSet<BlockRef>,
    blocks: Vec<BlockRef>,
    degree: usize,
}

impl Sudoku {
    pub fn new(degree: usize) -> Sudoku {
        // if degree = 3, normal sudoku. 3x3 = 9 cells
        let mut cells = HashMap::new();
        for x in 0..degree.pow(2) {
            for y in 0..degree.pow(2) {
                let pos = Coords {
                    x: x,
                    y: y,
                };
                let cell = Cell::new(pos.clone(), degree);
                cells.insert(pos, CellRef(Rc::new(RefCell::new(cell))));
            }
        }

        let blocks = Sudoku::gen_blocks(&cells, degree);

        Sudoku {
            cells: cells,
            blocks: blocks,
            degree: degree,
            update_req_blocks: BTreeSet::new(),
        }
    }

    fn gen_blocks(cells: &HashMap<Coords, CellRef>, degree: usize) -> Vec<BlockRef> {
        let mut map_x = HashMap::new();
        let mut map_y = HashMap::new();
        let mut map_g = HashMap::new();

        for val in cells.values() {
            let x = val.0.borrow().pos.x;
            let y = val.0.borrow().pos.y;
            let grid = (x / degree, y / degree);

            map_x.entry(x).or_insert(Vec::new()).push(val.clone());
            map_y.entry(y).or_insert(Vec::new()).push(val.clone());
            map_g.entry(grid).or_insert(Vec::new()).push(val.clone());
        }

        let mut blocks = Vec::new();
        blocks.append(&mut map_x.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("bx_{}", i));
            Block::create(name, cs.clone(), degree)
        }).collect::<Vec<_>>());
        blocks.append(&mut map_y.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("by_{}", i));
            Block::create(name, cs.clone(), degree)
        }).collect::<Vec<_>>());
        blocks.append(&mut map_g.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("bg_{}", i));
            Block::create(name, cs.clone(), degree)
        }).collect::<Vec<_>>());
        blocks
    }

    pub fn assign(&mut self, coords: &Coords, value: usize) -> Result<(), ()> {
        match self.cells.get_mut(coords) {
            Some(cell) => {
                let update_req_blocks = cell.0.borrow_mut().assign(value);
                for b in update_req_blocks {
                    self.update_req_blocks.insert(b);
                }
                Ok(())
            },
            None => {
                Err(())
            },
        }
    }

    pub fn inference(&mut self) {
        while true {
            println!("youjo {:?}", self.update_req_blocks);
            let mut b_ref_opt = None;
            for _b_ref in self.blocks.iter() {
                if self.update_req_blocks.contains(&_b_ref) {
                    self.update_req_blocks.remove(&_b_ref);
                    b_ref_opt = Some(_b_ref.clone());
                    break;
                }
            }
            match b_ref_opt {
                Some(b_ref) => {
                    b_ref.0.borrow_mut().inference();
                },
                None => {
                    break
                },
            }
        }
    }

    fn solve(&mut self) {
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn it_works() {
        let mut sudoku = Sudoku::new(4);
        sudoku.solve();
    }
}
