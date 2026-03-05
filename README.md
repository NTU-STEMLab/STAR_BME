# STAR-BME — Space-Time Analytics and Rendering Tool using Bayesian Maximum Entropy

<p align="center">
  <img src="image/stemlab.png" alt="STAR-BME Logo" width="160"/>
</p>

**STAR-BME** is a [QGIS](https://qgis.org) plugin for modern spatiotemporal modelling and mapping built upon the Bayesian Maximum Entropy (BME) geostatistical framework. It is developed and maintained by the [STEMLab (SpatioTemporal Environmental InforMatics Laboratory)](https://stemlab.bse.ntu.edu.tw) at National Taiwan University.

> 📖 Official page: [https://stemlab.bse.ntu.edu.tw/blog/2019-04-23-star-bme/](https://stemlab.bse.ntu.edu.tw/blog/2019-04-23-star-bme/)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Method 1: Install via QGIS Plugin Manager (Recommended)](#method-1-install-via-qgis-plugin-manager-recommended)
  - [Method 2: Manual Installation from ZIP](#method-2-manual-installation-from-zip)
  - [Method 3: Install from Source (Developer)](#method-3-install-from-source-developer)
  - [Python Dependency Installation](#python-dependency-installation)
    - [Option A – Automatic (First Launch Dialog)](#option-a--automatic-first-launch-dialog)
    - [Option B – Windows: OSGeo4W Shell (Recommended for Windows)](#option-b--windows-osgeo4w-shell-recommended-for-windows)
    - [Option C – macOS / Linux: System Terminal](#option-c--macos--linux-system-terminal)
    - [Option D – QGIS Python Console (All Platforms)](#option-d--qgis-python-console-all-platforms)
    - [Verifying Installation](#verifying-installation)
- [Quick Start](#quick-start)
- [Supported Data Formats](#supported-data-formats)
- [Example Datasets](#example-datasets)
- [Changelog](#changelog)
- [Authors and Contact](#authors-and-contact)
- [License](#license)

---

## Overview

STAR-BME implements the modern geostatistical framework proposed by Christakos (1991, 2000). Unlike conventional geostatistical methods, the BME framework extends spatial analysis into an *epistemic* approach that can:

- Synthesise **multi-sourced** space-time data of different formats and uncertainty levels
- Handle both **hard (exact) data** and **soft (uncertain/probabilistic) data**
- Generate meaningful space-time probability functions and associated maps

The plugin is built for **QGIS 3.x** (Python 3 / PyQt5) and provides a full graphical interface within QGIS for performing end-to-end spatiotemporal analysis without leaving the GIS environment.

---

## Key Features

1. **Integration of multi-sourced space-time data** in different data formats
2. **Incorporation of multi-sourced uncertainties** (hard and soft data support)
3. **Space-time dependence analysis** — empirical and mathematical spatiotemporal covariance models
4. **BME estimation and mapping** across space and time
5. **Cross-validation** with error statistics and spatial result display
6. **Data export** in multiple formats
7. **Easy display** of space-time data with time-bar navigation and colorbar controls
8. **Parallel processing** support via multi-threading for large datasets
9. **Automatic Python dependency management** — missing packages are detected and installed at first launch

---

## Requirements

| Requirement | Version |
|---|---|
| **QGIS** | 3.16 or later (up to 3.99) |
| **Python** | 3.x (bundled with QGIS) |
| **Operating System** | Windows (XP/7/8/10/11), macOS (10.8+), Linux (Ubuntu) |

### Python Package Dependencies

The following packages are required and will be **automatically installed** on first launch if missing:

| Package | Purpose |
|---|---|
| `numpy` | Numerical array operations |
| `scipy` (≥ 0.18) | Scientific computing, numerical integration |
| `pandas` | Data loading and management |
| `matplotlib` | Plotting and visualisation |

Optional (for advanced statistical features):

| Package | Purpose |
|---|---|
| `nlopt` (≥ 2.4) | Non-linear optimisation (BOBYQA) |
| `rpy2` (≥ 2.8) | R integration (requires R ≥ 3.4 with `dlnm`, `mgcv`) |

---

## Installation

### Method 1: Install via QGIS Plugin Manager (Recommended)

> ⚠️ This method requires the plugin to be listed in the QGIS official plugin repository. If it is not yet listed, use Method 2 or 3.

1. Open **QGIS**.
2. Go to **Plugins → Manage and Install Plugins…**
3. In the search bar, type `STAR BME`.
4. Select **STAR BME** from the results and click **Install Plugin**.
5. After installation, the plugin will appear under **Vector → STAR** in the menu bar.

---

### Method 2: Manual Installation from ZIP

1. Download the latest release ZIP file from the [Releases page](../../releases) or from the [official website](https://stemlab.bse.ntu.edu.tw/blog/2019-04-23-star-bme/).

2. Open **QGIS**.

3. Go to **Plugins → Manage and Install Plugins… → Install from ZIP**.

4. Browse to the downloaded ZIP file and click **Install Plugin**.

5. After installation completes, enable the plugin:
   - Go to **Plugins → Manage and Install Plugins… → Installed**
   - Find **STAR BME** and tick the checkbox to enable it.

6. The plugin will now appear under **Vector → STAR** in the QGIS menu bar.

---

### Method 3: Install from Source (Developer)

1. **Clone this repository** into the QGIS user plugins folder:

   **macOS / Linux:**
   ```bash
   cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
   git clone <repository-url> STAR_BME
   ```

   **Windows:**
   ```cmd
   cd %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
   git clone <repository-url> STAR_BME
   ```

   > **Note:** The folder name must match the plugin's internal module name. Use `STAR_BME` as the target directory name.

2. **Restart QGIS** (or use the Plugin Reloader plugin if installed).

3. Enable the plugin via **Plugins → Manage and Install Plugins… → Installed → STAR BME**.

---

### Python Dependency Installation

STAR-BME requires `numpy`, `scipy`, `pandas`, and `matplotlib`. These are **not bundled** with the standard QGIS installer and must be installed separately into the QGIS Python environment. Four options are available — choose the one that best fits your platform and situation.

---

#### Option A — Automatic (First Launch Dialog)

On first launch, STAR-BME automatically checks for missing packages. If any are absent, a dialog will appear asking for permission to install them.

1. Click **Yes** when prompted.
2. QGIS may appear unresponsive for several minutes while packages download — this is normal.
3. When the success dialog appears, **restart QGIS** to load the newly installed packages.

> ⚠️ If the dialog does not appear, or if automatic installation fails, proceed to one of the manual options below.

---

#### Option B — Windows: OSGeo4W Shell (Recommended for Windows)

This is the most reliable method on Windows. The OSGeo4W Shell is a special command prompt that automatically activates the exact Python environment used by QGIS.

1. **Open the OSGeo4W Shell:** Search for **"OSGeo4W Shell"** in the Windows Start Menu.

2. **Activate the QGIS Python environment:**
   ```cmd
   py3_env
   ```

3. **Install all required packages:**
   ```cmd
   python -m pip install numpy scipy pandas matplotlib
   ```

4. **Restart QGIS** to load the installed libraries.

To **verify** the installation:
```cmd
python -m pip list
```
Look for `numpy`, `scipy`, `pandas`, and `matplotlib` in the output.

To **uninstall** a package if needed:
```cmd
python -m pip uninstall pandas
```
*(Type `y` and press Enter to confirm.)*

---

#### Option C — macOS / Linux: System Terminal

1. **Open a Terminal.**

2. *(Ubuntu/Debian only — install pip if missing)*:
   ```bash
   sudo apt-get install python3-pip
   ```

3. **Install all required packages** using the Python interpreter bundled with QGIS. Replace the path below with your actual QGIS Python prefix if it differs:

   **macOS (QGIS.app bundle):**
   ```bash
   # Find the correct Python first
   /Applications/QGIS.app/Contents/MacOS/bin/python3 -m pip install numpy scipy pandas matplotlib
   ```

   **Linux:**
   ```bash
   python3 -m pip install numpy scipy pandas matplotlib
   ```

4. **Restart QGIS.**

To **uninstall** a package:
```bash
python3 -m pip uninstall pandas
```

> 💡 **macOS note:** On macOS, `sys.executable` inside QGIS may point to a wrapper script rather than the real Python binary. STAR-BME's auto-installer handles this by searching for `python3` under `sys.prefix/bin/`. If you see errors related to the Python path, see [Option D](#option-d--qgis-python-console-all-platforms) to confirm the exact path being used.

---

#### Option D — QGIS Python Console (All Platforms)

Use this method when you cannot access a system shell, or when other methods fail. The QGIS Python Console runs code inside the same Python process as QGIS, so packages installed here are immediately available.

**Open the console:** Go to **Plugins → Python Console** (or press `Ctrl+Alt+P` on Windows/Linux, `Cmd+Alt+P` on macOS).

---

**Method D-1: Using `subprocess` (Most Reliable)**

This approach calls `pip` as an external subprocess, which avoids permission and environment conflicts:

```python
import subprocess, sys, os

# Detect the correct Python interpreter for this QGIS installation
python_exe = os.path.join(sys.prefix, 'bin', 'python3')
print(f'Using Python: {python_exe}')  # Confirm the path before proceeding

# Install all required packages
subprocess.run(
    [python_exe, '-m', 'pip', 'install', '--user',
     'numpy', 'scipy', 'pandas', 'matplotlib'],
    check=True
)
print("Done! Please restart QGIS.")
```

> **Restart QGIS** after running this script.

---

**Method D-2: Using `pip` directly inside the console**

A simpler alternative that installs packages into the running QGIS session:

```python
import pip
pip.main(['install', 'numpy'])
pip.main(['install', 'scipy'])
pip.main(['install', 'pandas'])
pip.main(['install', 'matplotlib'])
```

> ⚠️ **Important:** This method installs packages into the *current* running session. Always **restart QGIS** afterward to ensure the packages are fully registered.

To **uninstall** via the console (the `-y` flag is required to prevent QGIS from hanging on the confirmation prompt):

```python
import pip
pip.main(['uninstall', 'pandas', '-y'])
```

---

#### Verifying Installation

After installing, confirm all packages are present by running the following in the **QGIS Python Console**:

```python
import numpy, scipy, pandas, matplotlib
print("numpy    :", numpy.__version__)
print("scipy    :", scipy.__version__)
print("pandas   :", pandas.__version__)
print("matplotlib:", matplotlib.__version__)
```

All four packages should print a version number without errors. If any raise an `ImportError`, re-run the installation for that specific package and restart QGIS.

You can also list all installed packages from the console:

```python
import subprocess, sys, os
python_exe = os.path.join(sys.prefix, 'bin', 'python3')
subprocess.run([python_exe, '-m', 'pip', 'list'])
```

---

## Quick Start

1. Launch QGIS and activate STAR-BME via **Vector → STAR → STAR-BME**.
2. Use **Set Data** to load your space-time dataset (`.csv`, `.xls`, `.xlsx`, or `.shp`).
3. Configure the covariance model in **Plot and Fit Covariance**.
4. Run **BME Estimation** to generate space-time predictions.
5. Optionally, run **Cross-Validation** to evaluate model performance.
6. Results are displayed as raster layers in the QGIS canvas with time-bar navigation.

For detailed usage instructions, refer to the official manuals available on the [STAR-BME webpage](https://stemlab.bse.ntu.edu.tw/blog/2019-04-23-star-bme/).

---

## Supported Data Formats

| Format | Description |
|---|---|
| `.csv` | Comma-separated values |
| `.xls` / `.xlsx` | Microsoft Excel spreadsheets |
| `.shp` | ESRI Shapefiles |

---

## Example Datasets

Example datasets (with data and step-by-step manuals) are available for download from the [official website](https://stemlab.bse.ntu.edu.tw/blog/2019-04-23-star-bme/):

- **BlackDeath** — Historical plague spread data
- **PM10** — Particulate matter (PM10) air quality data
- **PM2.5** — Fine particulate matter air quality data
- **Ozone** — Ground-level ozone concentration data

---

## Changelog

### v1.0.0 — Major Release (2026-02-26)
Full migration from Python 2 / PyQt4 / QGIS 2 to **Python 3.12 / PyQt5 / QGIS 3.x**.

Key improvements:
- **Cross-Validation:** Fixed multiprocessing deadlock on macOS; resolved GUI freezing; replaced slow cubature integration with faster QMC-based engine; improved NaN handling and result labelling.
- **BME Estimation:** Improved numerical stability with QMC domain clipping, PSD enforcement, Importance Sampling, automatic Gaussian approximation fallback, and robust SVD; added non-negativity constraint support; implemented parallel prediction via `ThreadPoolExecutor`.
- **GUI:** Fixed rendering errors in variance display; fixed colorbar crashes; updated dynamic colorbar labels; fixed matplotlib 3.x compatibility.
- **QGIS 3 API:** Updated `QgsMapLayerRegistry`, `QgsCoordinateReferenceSystem`, `QgsVectorFileWriter`, `QgsGraduatedSymbolRenderer`, and `QgsField` calls to current QGIS 3 APIs.
- **Python 3.12:** Replaced `imp` with `importlib`; fixed integer division, `long` type, and `print` statements; replaced deprecated `numpy` types.

### v0.6.0
Updated for QGIS 3 compatibility.

---

## Authors and Contact

**STEMLab — SpatioTemporal Environmental InforMatics Laboratory**  
Department of Bioenvironmental Systems Engineering  
National Taiwan University (NTU)

- **Maintainer:** hlyu@ntu.edu.tw
- **Website:** [https://stemlab.bse.ntu.edu.tw](https://stemlab.bse.ntu.edu.tw)

---

## License

Please refer to the license terms provided by STEMLab / NTU BSE. For inquiries regarding usage, redistribution, or collaboration, contact the maintainers at the email above.

---

*STAR-BME is based on the BME framework: Christakos, G. (1990). A Bayesian/maximum-entropy view to the spatial estimation problem. Mathematical Geology, 22(7), 763–777.*
