use std::sync::{Arc, RwLock, Weak};
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};

extern crate bit_vec;
use self::bit_vec::BitVec;

#[derive(Hash, Eq, PartialEq, Clone, Debug)]
struct Coords {
    pub x: usize,
    pub y: usize,
}


#[derive(Debug)]
struct Cell {
    // 1 x 1 cell
    pos: Coords,
    blocks: HashSet<BlockWeak>,
    pub value: Option<usize>,
    pub possibles: BitVec,
}

type CellPtr = Arc<RwLock<Cell>>;

impl Cell {
    pub fn new(pos: Coords, degree: usize) -> Cell {
        let num = degree * degree;
        Cell {
            pos: pos,
            value: None,
            blocks: HashSet::new(),
            possibles: BitVec::from_elem(num, true),
        }
    }

    pub fn assign(&mut self, value: usize) {
        self.value = Some(value);
        self.possibles.set_all();
        self.possibles.negate();
        self.possibles.set(value, true);
    }
}

#[derive(Debug)]
struct Block {
    // block which contains N cells
    name: String,
    cells: Vec<CellPtr>,
    assigned_values: BitVec,
    degree: usize,
}

impl Hash for Block {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.name.hash(state)
    }
}

struct BlockRef(Arc<RwLock<Block>>);
impl PartialEq for BlockRef {
    fn eq(&self, other: &BlockRef) -> bool {
        true // TODO
    }
}

impl Hash for BlockRef{
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.read().unwrap().hash(state);
    }
}

impl Eq for BlockRef {}



#[derive(Debug)]
struct BlockWeak(Weak<RwLock<Block>>);

impl PartialEq for BlockWeak {
    fn eq(&self, other: &BlockWeak) -> bool {
        true // TODO
    }
}

impl Hash for BlockWeak {
    fn hash<H: Hasher>(&self, state: &mut H) {
        let b = self.0.upgrade().unwrap();
        b.read().unwrap().hash(state);
    }
}

impl Eq for BlockWeak {}

impl Block {
    pub fn new(name :String, cells: &Vec<CellPtr>, degree: usize) -> Block {
        assert_eq!(cells.len(), degree * degree);
        let num = degree * degree;
        Block {
            name: name,
            cells: cells.clone(),
            assigned_values: BitVec::from_elem(num, false),
            degree: degree,
        }
    }

    pub fn inference(&self) -> Result<HashSet<BlockRef>, ()>{
        let update_req_blocks = HashSet::new();
        for c_ref in self.cells.iter()
            .filter(|c| c.read().unwrap().possibles != self.assigned_values) {
                let mut c = c_ref.write().unwrap(); 
                c.possibles.intersect(&self.assigned_values);
                if c.possibles.none() {
                    return Err(());
                }
                update_req_blocks.union(&c.blocks);
        }
        let res = update_req_blocks.iter().map(|b|BlockRef(b.0.upgrade().unwrap())).collect::<HashSet<_>>();
        return Ok(res);
    }

    pub fn update_assigned_values(&mut self) {
        let mut assigned_values = BitVec::from_elem(self.degree, false);
        for c in self.cells.iter() {
            assigned_values.union(&c.read().unwrap().possibles);
        }
        self.assigned_values = assigned_values;
    }
}


pub struct Sudoku {
    cells: HashMap<Coords, CellPtr>,
    blocks: Vec<BlockRef>,
    degree: usize,
}

impl Sudoku {
    pub fn new(degree: usize) -> Sudoku {
        // if degree = 3, normal sudoku. 3x3 = 9 cells
        let mut cells = HashMap::new();
        for x in 1..(degree * degree + 1) {
            for y in 1..(degree * degree + 1) {
                let pos = Coords {
                    x: x,
                    y: y,
                };
                let cell = Cell::new(pos.clone(), degree);
                cells.insert(pos, Arc::new(RwLock::new(cell)));
            }
        }

        let blocks = Sudoku::gen_blocks(&cells, degree);

        Sudoku {
            cells: cells,
            blocks: blocks,
            degree: degree,
        }
    }

    fn gen_blocks(cells: &HashMap<Coords, CellPtr>, degree: usize) -> Vec<BlockRef> {
        let mut map_x = HashMap::new();
        let mut map_y = HashMap::new();
        let mut map_g = HashMap::new();

        for val in cells.values() {
            let x = val.read().unwrap().pos.x;
            let y = val.read().unwrap().pos.y;
            let grid = ((x - 1) / degree, (y - 1) / degree);

            map_x.entry(x).or_insert(Vec::new()).push(val.clone());
            map_y.entry(y).or_insert(Vec::new()).push(val.clone());
            map_g.entry(grid).or_insert(Vec::new()).push(val.clone());
        }

        let mut blocks = Vec::new();
        blocks.append(&mut map_x.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("bx_{}", i));
            Block::new(name, cs, degree)
        }).collect::<Vec<_>>());
        blocks.append(&mut map_y.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("by_{}", i));
            Block::new(name, cs, degree)
        }).collect::<Vec<_>>());
        blocks.append(&mut map_g.values().enumerate().map(|(i,cs)| {
            let name = String::from(format!("bg_{}", i));
            Block::new(name, cs, degree)
        }).collect::<Vec<_>>());
        blocks.into_iter().map(|b| BlockRef(Arc::new(RwLock::new(b)))).collect::<Vec<_>>()
    }

    fn assign(&mut self, coords: &Coords, value: usize) -> Result<(), ()> {
        match self.cells.get(coords) {
            Some(cell) => {
                cell.write().unwrap().assign(value);
                Ok(())
            },
            None => {
                Err(())
            },
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
    }
}
