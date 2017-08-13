use std::env;

mod sudoku;
mod reader;


fn main() {
    let mut sudoku = sudoku::Sudoku::new(3);
    sudoku.inference();

    let mut args = env::args();
    let filepath = args.nth(1).unwrap();

    let mut sudoku = reader::read_csv(filepath).unwrap();
    sudoku.inference();
}
