# MURA - MOTH
- Masarky Unversity Research Analyzer
- MUNI Open-source Tutoring Helper

This project uses Jupyter Notebooks. All the necessary information on how to use the tool are written in there.

## Installation

### Requirements

Python 3.9 or higher (Lower version may also be functional, but are generally not supported)\
Docker reasonably up to date

1) Setup a virtual environment (All commands are run in the current directory)

**Linux/Mac**
```bash
python3 -m venv ./venv
```
**Windows powershell**
```ps1
python -m venv ./venv
```

In case your system does not come with the `venv` module, you should be presented with the correct command for your distribution to install it. 

Activate the virtual environment

```bash
./venv/bin/activate
```

Note: On linux distributions you may need to run `source ./venv/bin/activate` to execute the script.

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