# MURA - MOTH
- Masarky Unversity Research Analyzer
- MUNI Open-source Tutoring Helper

This project uses Jupyter Notebooks. All the necessary information on how to use the tool are written in there.

## Installation

### Requirements

Python 3.9 or higher
Docker reasonable up to date

1) Setup a virtual environment (All commands are run in the current directory)

**Linux/Mac**
```bash
python3 -m venv ./venv
```
**Windows powershell**
```ps1
python -m venv ./venv
```

Activate the virtual environment

```bash
./venv/bin/activate
```

Install the requirements

```bash
pip install -r requirements.txt
```

### Running the project

**Linux/Mac**
```bash
./venv/bin/jupyter notebook
```
**Windows Powershell**
```ps1
./venv/Script/jupyter.exe notebook
```

Locate and open the `main.ipynb` file from the browser interface.