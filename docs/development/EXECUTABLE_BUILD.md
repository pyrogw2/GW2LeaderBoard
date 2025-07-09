# Executable Builds

This document describes how to build and distribute executable versions of the GW2 WvW Leaderboard tool.

## Automated GitHub Actions Build

The repository includes GitHub Actions workflows that automatically build executables for Windows, macOS, and Linux when you create a version tag.

### Triggering a Build

1. **Create a version tag:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manual trigger:** Go to the Actions tab in GitHub and manually run the "Build Executables" workflow.

### Generated Files

The build process creates:
- **Windows**: `workflow_ui.exe` - Single executable file
- **macOS**: `GW2 Leaderboard.app` - Application bundle + DMG installer
- **Linux**: `gw2-leaderboard` - Single executable binary

## Manual Local Building

### Prerequisites

```bash
pip install pyinstaller
pip install -r requirements.txt
```

### Windows Executable

```bash
pyinstaller workflow_ui.spec
```

This creates `dist/workflow_ui.exe`.

### macOS Application Bundle

```bash
pyinstaller --windowed --onefile \
  --name "GW2 Leaderboard" \
  --add-data "src:src" \
  workflow_ui.py
```

### Linux Binary

```bash
pyinstaller --onefile \
  --name "gw2-leaderboard" \
  --add-data "src:src" \
  workflow_ui.py
```

## Distribution Package Contents

Each executable package includes:
- Main executable file
- `README.md` - Main documentation
- `sync_config.json.example` - Configuration template

## Usage

1. **First run**: Copy `sync_config.json.example` to `sync_config.json`
2. **Configure**: Edit the configuration file with your settings
3. **Run**: Double-click the executable (Windows/macOS) or run from terminal (Linux)

## Configuration

The GUI application uses the same configuration format as the command-line version:

```json
{
  "log_aggregate_url": "https://pyrogw2.github.io",
  "database_path": "gw2_comprehensive.db",
  "web_ui_output": "web_ui_final",
  "guild": {
    "api_key": "your-gw2-api-key",
    "guild_id": "your-guild-id",
    "filter_enabled": true
  }
}
```

## Troubleshooting

### Windows

- **Antivirus warnings**: Some antivirus software may flag PyInstaller executables. This is a false positive.
- **Missing DLLs**: The executable should be self-contained, but you may need Visual C++ Redistributables.

### macOS

- **Security warnings**: You may need to right-click and "Open" the first time due to Gatekeeper.
- **Permissions**: The app may need permission to access the internet and write files.

### Linux

- **GTK/Tkinter issues**: Make sure you have `python3-tk` installed on the system.
- **Permissions**: Make the binary executable with `chmod +x gw2-leaderboard`.

## Build Requirements

The automated builds require:

- **Python 3.11**: For compatibility and performance
- **Minimal dependencies**: Only `requests` and `beautifulsoup4`
- **Cross-platform support**: Tkinter for GUI (included with Python)

## File Sizes

Typical executable sizes:
- **Windows**: ~15-20 MB (single .exe)
- **macOS**: ~18-25 MB (app bundle)
- **Linux**: ~20-25 MB (single binary)

## Development Notes

- The `workflow_ui.spec` file configures PyInstaller for Windows builds
- The `src` directory is bundled with executables for module imports
- GUI redirects stdout/stderr to the built-in console for debugging
- All command-line functionality is available through the GUI interface

## Future Enhancements

Potential improvements for executable builds:
- Custom application icons
- Code signing for Windows/macOS
- Installer packages (MSI, PKG, DEB/RPM)
- Auto-updater functionality
- Embedded web server for viewing results directly in the app