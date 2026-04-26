# Microsoft Flight Simulator 2024 Settings Dashboard

A small Windows GUI tool for editing selected Microsoft Flight Simulator 2024 configuration settings from one place.

The app is intentionally simple: it is a single Python/Tkinter script, uses only the Python standard library, and writes numbered backups before saving any simulator configuration file.

## What It Edits

The dashboard reads and writes configuration files in the same folder as the app:

- `UserCfg.opt`
- `FlightSimulator2024.CFG`
- `DevMode.xml`

The app includes tabs for video, graphics, traffic, VR, simulator UI/assistance options, developer-mode options, and backups. Missing files are tolerated; the app only edits files that exist in the folder.

## Safety

Before saving changes, the app creates numbered backup files next to the originals:

```text
UserCfg.opt.backup_001
UserCfg.opt.backup_002
FlightSimulator2024.CFG.backup_001
DevMode.xml.backup_001
```

Existing backups are never overwritten. The app also has a **Backups** tab where you can create backups manually without changing any settings.

## Requirements

- Windows 10 or Windows 11
- Microsoft Flight Simulator 2024
- Python 3.10 or newer

You do not need to install any Python packages with `pip`. Tkinter is included with the normal Python installer from python.org.

## Download

Use one of these options:

### Option 1: Download From GitHub

1. Open this repository on GitHub.
2. Click **Code**.
3. Click **Download ZIP**.
4. Extract the ZIP file.
5. Copy `MS_Setup.pyw` and `install_and_run.bat` into your Microsoft Flight Simulator 2024 configuration folder.

### Option 2: Clone With Git

```powershell
git clone https://github.com/klusik/FS24_settings_dashboard.git
```

Then copy these files from the cloned folder into your Microsoft Flight Simulator 2024 configuration folder:

- `MS_Setup.pyw`
- `install_and_run.bat`

## Where To Put The Files

Put `MS_Setup.pyw` and `install_and_run.bat` in the same folder as the simulator configuration files you want to edit.

The correct folder is the one that contains one or more of these files:

- `UserCfg.opt`
- `FlightSimulator2024.CFG`
- `DevMode.xml`

Common places to check include:

```text
%LOCALAPPDATA%\Packages\
%APPDATA%\
```

The exact Microsoft Flight Simulator 2024 configuration location can vary by install type, Store/Xbox app vs Steam, and user profile. If you are unsure, search your Windows user folder for `UserCfg.opt`, then place this tool in that same folder.

## Run On Windows By Double-Clicking

The easiest way to run the app is:

1. Put `install_and_run.bat` next to `MS_Setup.pyw`.
2. Put both files next to your simulator configuration files.
3. Double-click `install_and_run.bat`.

The batch file is the universal launcher:

- It checks whether Python 3.10 or newer is installed.
- If a suitable Python is found, it starts `MS_Setup.pyw`.
- If Python is missing or too old, it installs Python 3.12 for the current Windows user.
- After installing Python, it starts the dashboard with that Python.
- After the dashboard starts, the batch window closes so only the app remains visible.

The installer does not require administrator rights by default because it installs Python only for the current Windows user.

## Run Manually

If Python is already installed, you can also run the app directly:

```powershell
py MS_Setup.pyw
```

or:

```powershell
python MS_Setup.pyw
```

Run the command from the folder that contains `MS_Setup.pyw`.

## How To Use

1. Start the app.
2. Review the folder shown at the top of the window. It should be your simulator configuration folder.
3. Change settings in the tabs.
4. Click **Create Backups Now** if you want an extra backup before editing.
5. Click **Save Changes** to write the settings.
6. Restart Microsoft Flight Simulator 2024 if the simulator was already running.

## Files In This Repository

```text
MS_Setup.pyw          Main Tkinter dashboard application
install_and_run.bat  Windows launcher and Python installer helper
README.md            Project documentation
```

## Troubleshooting

### Windows SmartScreen Warns About The Batch File

Windows may warn about downloaded `.bat` files. Open the file in a text editor if you want to inspect it first. It checks for Python, installs Python for the current user if needed, and starts `MS_Setup.pyw`.

### The App Opens But Shows Empty Or Default Values

Make sure `MS_Setup.pyw` is in the same folder as the simulator config files. The app reads files from its own folder, not from the current terminal folder or a guessed global path.

### Python Installation Fails

Install Python manually from:

```text
https://www.python.org/downloads/windows/
```

During installation, enable **Add python.exe to PATH** if the installer offers that option. Then run `install_and_run.bat` again.

### Changes Do Not Appear In The Simulator

Close Microsoft Flight Simulator 2024 before saving settings, then start it again after saving. Some settings are only read by the simulator during startup.

### I Need To Restore A Backup

Backups are stored in the same folder as the original files. To restore one:

1. Close Microsoft Flight Simulator 2024.
2. Rename the current config file, for example `UserCfg.opt` to `UserCfg.opt.current`.
3. Rename the backup you want to restore, for example `UserCfg.opt.backup_001` to `UserCfg.opt`.
4. Start the simulator again.

## Development Notes

This project is deliberately dependency-free. The GUI is built with Tkinter, and config parsing uses only Python standard library modules:

- `configparser`
- `pathlib`
- `shutil`
- `tkinter`
- `xml.etree.ElementTree`

That makes the tool easy to run on a normal Windows machine without a virtual environment or package installation.
