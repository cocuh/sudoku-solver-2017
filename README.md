# usage
```
usage: solve.py [-h] [--output OUTPUT] [--parallel] [--debug] [--one]
                problem_csv

positional arguments:
  problem_csv

optional arguments:
  -h, --help       show this help message and exit
  --output OUTPUT
  --parallel       solve with cpu_num worker processes if specified, default
                   is single threading
  --debug
  --one            if you want to one solution.
```

## Example: problem csv
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
## with parallel
```shell
$ python solve.py --parallel test_data/ill-posed/9x9.csv
...
#solutions = 507
spend time(sec) = 2.611497163772583

$ python solve.py --parallel test_data/ill-posed/16x16.csv
...
#solutions = 20
spend time(sec) = 33.79838275909424
```

## with single
```shell
$ python solve.py test_data/ill-posed/9x9.csv
...
#solutions = 507
spend time(sec) = 6.469801902770996

$ python solve.py test_data/ill-posed/16x16.csv
...
#solutions = 20
spend time(sec) = 77.15005278587341
```