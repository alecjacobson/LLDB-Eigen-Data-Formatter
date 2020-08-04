# LLDB Eigen Data Formatter

LLDB Data Formatter for dense matrices and vectors of the [Eigen](http://eigen.tuxfamily.org) library.

## Example

```cpp
Eigen::Matrix<double, 3, 4> A;
A << 1, 2, 3, 4,
    5, 6, 7, 8,
    9, 10, 11, 12;
```

Corresponding output in LLDB

```
(lldb) print A
(Eigen::Matrix<double, 3, 4, 0, 3, 4>) $2 = rows: 3, cols: 4
[ 1   2   3   4;
  5   6   7   8;
  9  10  11  12;
]
```

## Installation

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/tehrengruber/LLDB-Eigen-Data-Formatter/master/tools/install.sh)"
```

__Manual Installation__

```bash
INSTALL_PATH=~/.lldb-eigen-data-formatter
git clone https://github.com/tehrengruber/LLDB-Eigen-Data-Formatter.git $INSTALL_PATH
echo 'command script import "'$INSTALL_PATH'/LLDB_Eigen_Data_Formatter.py"' >> ~/.lldbinit
```

__Uninstallation__

```bash
rm -fr ~/.lldb-eigen-data-formatter
```

Afterwards remove the `command script import` command in `~/.lldbinit`.

## License

Copyright © 2016 Till Ehrengruber

Distributed under the GNU GENERAL PUBLIC LICENSE.
