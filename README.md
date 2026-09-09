# mmcalc

Calculational proofs for [Metamath](https://us.metamath.org/).

## Overview

mmcalc provides a text file format for writing calculational proofs (structured derivations) for Metamath statements, and a tool that can read such files and extract Metamath proofs from them.

This is based on the [calculational proof format idea](https://groups.google.com/g/metamath/c/aNki7h6G50A/m/-hsjesajGAAJ) for Metamath.

## Requirements

- Python >= 3.10
- [metamath-knife](https://github.com/metamath/metamath-knife) (must be installed and on PATH)

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Usage

```bash
# Verify a Metamath database
mmcalc verify path/to/database.mm

# Parse an mmcalc proof file
mmcalc parse path/to/proof.mcalc

# List statements in a database
mmcalc statements path/to/database.mm

# Show database outline
mmcalc outline path/to/database.mm
```

## License

This is free and unencumbered software released into the public domain.
See [LICENSE](LICENSE) for details.
