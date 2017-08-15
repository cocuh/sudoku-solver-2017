# usage
```
usage: solve.py [-h] [--output OUTPUT] [--parallel] [--debug] [--one]
                problem_csv

positional arguments:
  problem_csv

optional arguments:
  -h, --help       show this help message and exit
  --output OUTPUT  default: stdout
  --parallel       solve with cpu_num*2 worker processes if specified, 
                   default: single threading
  --debug
  --one            if you want only one solution.
```

## input: problem csv
### 9x9
```
 , ,9,4, , ,8,5, 
5, , ,7, , ,4, , 
2,8, ,1, , , , , 
 ,9,5, , ,1, , , 
 ,1, , ,6, , ,4, 
 , , ,9, , ,5,7, 
 , , , , ,9, ,6,4
 , ,7, , ,5, , ,9
 ,4,8, , ,7,3, , 
```

### 16x16
```
  ,  , 5,  , 7,  ,  ,  , 6,  ,  ,  ,11,  ,  , 1
  ,  ,11, 3,14,  ,  , 4,16, 9,  ,  ,  ,  , 8, 6
15,  ,  ,  ,  ,  , 5, 1,10,  ,  ,  ,  ,14,  ,  
 9, 4,  , 2,  ,13,  , 6, 1,14,  ,15,  ,  ,12,  
  ,  , 7,  , 4,  , 6, 9,  , 2,  ,  ,  ,15,  ,  
  ,  , 8,  ,  ,  ,13, 2,  , 3,10,  ,  ,  ,  ,  
  ,  , 6,12,  ,  ,15, 7,  ,  ,  ,  , 1,  ,  ,  
  ,  ,  ,  ,  ,  ,  ,  ,12,  ,  ,  ,  , 6,  , 9
  ,  ,  ,  ,  ,10,  ,  ,  , 5,  ,  ,  ,  ,  ,  
  ,  , 9,  , 5,  ,  , 3,  ,  ,  ,  ,16,  , 2,  
  , 2,  ,15,  ,  , 9,  ,11,  ,12, 4,  ,  , 5,14
11,  ,12,  ,16,  ,  ,  ,  , 8,  ,  , 3, 7,  , 4
10, 3,  , 6,  ,  ,  ,  , 2,  ,14,  , 7, 8, 4,  
  ,14,  ,  , 2,  ,  ,  ,  ,  ,  ,  ,  ,10,  ,15
  , 7,15,  ,  , 8,  ,  ,  ,  , 9,  , 5,  ,  ,  
  , 5,  ,  ,  ,  ,11,  ,  ,12,16, 8,  ,  ,  ,  
```

# benchmark

## well-posed
```shell
$ python solve.py --parallel test_data/well-posed/9x9.csv
 , ,9|4, , |8,5, 
5, , |7, , |4, , 
2,8, |1, , | , , 
-----------------
 ,9,5| , ,1| , , 
 ,1, | ,6, | ,4, 
 , , |9, , |5,7, 
-----------------
 , , | , ,9| ,6,4
 , ,7| , ,5| , ,9
 ,4,8| , ,7|3, , 

SATISFIABLE: well-posed problem
#solutions = 1
spend time(sec) = 0.027388572692871094

solution 1/1
1,7,9|4,2,6|8,5,3
5,3,6|7,9,8|4,1,2
2,8,4|1,5,3|6,9,7
-----------------
4,9,5|8,7,1|2,3,6
7,1,3|5,6,2|9,4,8
8,6,2|9,3,4|5,7,1
-----------------
3,5,1|2,8,9|7,6,4
6,2,7|3,4,5|1,8,9
9,4,8|6,1,7|3,2,5

#solutions = 1
spend time(sec) = 0.027388572692871094


$ python solve.py --parallel test_data/well-posed/16x16.csv
...
#solutions = 1
spend time(sec) = 0.06147480010986328

$ python solve.py --parallel test_data/well-posed/25x25.csv
...
#solutions = 1
spend time(sec) = 76.580557346344
```

## ill-posed
### in parallel
```shell
$ python solve.py --parallel test_data/ill-posed/9x9.csv
...
#solutions = 507
spend time(sec) = 1.9318995475769043

$ python solve.py --parallel test_data/ill-posed/16x16.csv
...
#solutions = 20
spend time(sec) = 1.1831660270690918

$ python solve.py --parallel test_data/ill-posed/16x16_2.csv
...
#solutions = 1054
spend time(sec) = 21.00856924057007
```

### in single threading
```shell
$ python solve.py test_data/ill-posed/9x9.csv
...
#solutions = 507
spend time(sec) = 5.77640438079834

$ python solve.py test_data/ill-posed/16x16.csv
...
#solutions = 20
spend time(sec) = 1.912825584411621

$ python solve.py test_data/ill-posed/16x16_2.csv
#solutions = 1054
spend time(sec) = 59.848926305770874
```
