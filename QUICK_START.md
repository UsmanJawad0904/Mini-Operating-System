# MiniOS Quick Start

## Recommended app
Use **VS Code** for editing/running the project.

## Run on Windows

1. Install Python 3.10+ from python.org.
2. Open this folder in VS Code.
3. Open Terminal in VS Code.
4. Create a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

5. Install requirements:

```bash
pip install -r requirements.txt
```

6. Start the GUI:

```bash
python main.py
```

Or double-click `start_gui.bat`.

## CLI version

```bash
python cli.py
```

## Useful keys

- `Esc` exits fullscreen.
- `F11` toggles fullscreen.

## Notes

- The folder `MiniOS_Devices/` is generated automatically for local device data.
- Do not upload `.venv/`, `__pycache__/`, or `MiniOS_Devices/` to GitHub.
