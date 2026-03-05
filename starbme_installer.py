# -*- coding: utf-8 -*-
"""
STAR_BME Dependency Installer
Automatically checks and installs required Python packages
"""

import sys
import subprocess
import importlib.util

class DependencyInstaller:
    """Handles automatic installation of plugin dependencies"""
    
    REQUIRED_PACKAGES = {
        'numpy': 'numpy',
        'scipy': 'scipy', 
        'pandas': 'pandas',
        'matplotlib': 'matplotlib'
    }
    
    def __init__(self):
        self.missing_packages = []
        self.installation_log = []
        
    def check_dependencies(self):
        """Check which dependencies are missing"""
        self.missing_packages = []
        
        for display_name, package_name in self.REQUIRED_PACKAGES.items():
            if not self._is_package_available(package_name):
                self.missing_packages.append(package_name)
        
        return len(self.missing_packages) == 0
    
    def _is_package_available(self, package_name):
        """Check if a package is importable"""
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    
    def get_missing_packages_message(self):
        """Get user-friendly message about missing packages"""
        if not self.missing_packages:
            return None
        
        packages_str = ", ".join(self.missing_packages)
        return (
            f"STAR-BME requires the following Python packages:\n\n"
            f"{packages_str}\n\n"
            f"Would you like to install them automatically?\n\n"
            f"(This will run: pip install --user {packages_str})"
        )
    
    def _find_python_executable(self):
        """
        Find the correct Python executable for QGIS.
        
        Strategy:
        A. Use sys.prefix to construct path to python3 binary
        B. If that fails, recursively search QGIS.app bundle
        C. If all fails, log debug info and return sys.executable
        
        Returns:
            str: Path to Python executable
        """
        import os
        import stat
        
        exe = sys.executable
        
        # Debug logging
        print(f"[STAR_BME DEBUG] sys.executable = {exe}")
        print(f"[STAR_BME DEBUG] sys.prefix = {sys.prefix}")
        print(f"[STAR_BME DEBUG] sys.base_prefix = {getattr(sys, 'base_prefix', 'N/A')}")
        
        def is_valid_python(path):
            """Check if path is a valid, executable Python binary"""
            if not os.path.exists(path):
                return False
            if not os.path.isfile(path):
                return False
            # Check if executable
            try:
                return os.access(path, os.X_OK)
            except:
                return False
        
        # ========================================
        # STRATEGY A: Use sys.prefix
        # ========================================
        # Python is typically at {sys.prefix}/bin/python3
        prefix_python = os.path.join(sys.prefix, 'bin', 'python3')
        print(f"[STAR_BME DEBUG] Strategy A: Trying {prefix_python}")
        
        if is_valid_python(prefix_python):
            print(f"[STAR_BME DEBUG] ✅ Found via sys.prefix: {prefix_python}")
            return prefix_python
        
        # Also try base_prefix (for venv scenarios)
        if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            base_prefix_python = os.path.join(sys.base_prefix, 'bin', 'python3')
            print(f"[STAR_BME DEBUG] Strategy A.2: Trying {base_prefix_python}")
            if is_valid_python(base_prefix_python):
                print(f"[STAR_BME DEBUG] ✅ Found via sys.base_prefix: {base_prefix_python}")
                return base_prefix_python
        
        # ========================================
        # STRATEGY B: Recursive Search (Nuclear Option)
        # ========================================
        print(f"[STAR_BME DEBUG] Strategy A failed. Starting recursive search...")
        
        # Find QGIS.app root
        qgis_app_root = None
        if 'QGIS.app' in exe or 'QGIS.app' in sys.prefix:
            # Extract path to .app bundle
            for path_component in [exe, sys.prefix]:
                if 'QGIS.app' in path_component:
                    app_idx = path_component.find('QGIS.app')
                    qgis_app_root = path_component[:app_idx + len('QGIS.app')]
                    break
        
        if qgis_app_root and os.path.exists(qgis_app_root):
            print(f"[STAR_BME DEBUG] Strategy B: Searching inside {qgis_app_root}")
            
            # Walk through the bundle looking for python3 in bin/ folders
            found_pythons = []
            for root, dirs, files in os.walk(qgis_app_root):
                # Skip certain directories to speed up search
                if any(skip in root for skip in ['.git', '__pycache__', 'site-packages']):
                    continue
                
                if 'python3' in files:
                    python_path = os.path.join(root, 'python3')
                    if is_valid_python(python_path):
                        found_pythons.append(python_path)
                        print(f"[STAR_BME DEBUG] Found candidate: {python_path}")
                        
                        # Prefer python3 in a 'bin' directory
                        if 'bin' in root:
                            print(f"[STAR_BME DEBUG] ✅ Found via recursive search: {python_path}")
                            return python_path
            
            # If we found any python3, return the first one
            if found_pythons:
                print(f"[STAR_BME DEBUG] ✅ Using first found: {found_pythons[0]}")
                return found_pythons[0]
        
        # ========================================
        # STRATEGY C: Use sys.executable directly
        # ========================================
        # On some systems, sys.executable works with -m pip even if it's
        # not a direct Python binary (e.g., QGIS might have a wrapper)
        print(f"[STAR_BME DEBUG] Strategies A & B failed.")
        print(f"[STAR_BME DEBUG] Trying sys.executable directly: {exe}")
        print(f"[STAR_BME DEBUG] (This may work if QGIS has a Python wrapper)")
        
        return exe
    
    def install_dependencies(self):
        """Install missing dependencies using pip"""
        if not self.missing_packages:
            return True, "All dependencies already installed"
        
        python_exe = self._find_python_executable()
        
        # Try to install packages
        for package in self.missing_packages:
            success, message = self._install_package(python_exe, package)
            self.installation_log.append(f"{package}: {message}")
            
            if not success:
                return False, self._get_failure_message()
        
        return True, "All dependencies installed successfully!"
    
    def _install_package(self, python_exe, package):
        """Install a single package using pip"""
        try:
            # Large packages like pandas need more time
            timeout_map = {
                'pandas': 600,  # 10 minutes for pandas (it's large!)
                'matplotlib': 600,  # 10 minutes for matplotlib
                'scipy': 600,  # 10 minutes for scipy
                'numpy': 300,  # 5 minutes for numpy
            }
            timeout = timeout_map.get(package, 300)
            
            # Use --user flag to avoid permission issues
            cmd = [python_exe, "-m", "pip", "install", "--user", package]
            
            print(f"[STAR_BME DEBUG] Installing {package} (timeout: {timeout}s)...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, "Installed successfully"
            else:
                error_msg = result.stderr[:200] if result.stderr else result.stdout[:200]
                return False, f"Install failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, f"Installation timed out after {timeout}s (slow network?)"
        except Exception as e:
            return False, f"Error: {str(e)[:200]}"
    
    def _get_failure_message(self):
        """Generate detailed failure message with debug info"""
        python_exe = self._find_python_executable()
        
        msg = "Automatic installation failed.\n\n"
        
        # Add debug info
        msg += "Debug Information:\n"
        msg += f"  • sys.executable: {sys.executable}\n"
        msg += f"  • sys.prefix: {sys.prefix}\n"
        msg += f"  • Detected Python: {python_exe}\n"
        msg += "\n"
        
        msg += "Installation log:\n"
        for log_entry in self.installation_log:
            msg += f"  • {log_entry}\n"
        msg += "\n"
        msg += "Manual installation required:\n"
        msg += "1. Open QGIS Python Console (Ctrl+Alt+P or Cmd+Alt+P)\n"
        msg += "2. Run these commands:\n"
        msg += "   import subprocess, sys, os\n"
        msg += f"   python_exe = os.path.join(sys.prefix, 'bin', 'python3')\n"
        msg += "   print(f'Using Python: {{python_exe}}')\n"
        for package in self.missing_packages:
            msg += f"   subprocess.run([python_exe, '-m', 'pip', 'install', '--user', '{package}'])\n"
        msg += "\n3. Restart QGIS\n"
        msg += "\nIf above fails, check the QGIS Python Console output for debug info.\n"
        return msg


def ensure_dependencies(iface=None):
    """
    Main entry point for dependency checking and installation
    
    Args:
        iface: QGIS interface object (for showing message boxes)
        
    Returns:
        bool: True if all dependencies are available, False otherwise
    """
    from qgis.PyQt.QtWidgets import QMessageBox
    
    installer = DependencyInstaller()
    
    # Check if dependencies are available
    if installer.check_dependencies():
        return True
    
    # Show dialog asking user permission to install
    missing_msg = installer.get_missing_packages_message()
    
    if iface:
        reply = QMessageBox.question(
            iface.mainWindow(),
            "STAR-BME: Missing Dependencies",
            missing_msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            QMessageBox.information(
                iface.mainWindow(),
                "STAR-BME: Installation Cancelled",
                "Plugin cannot run without required dependencies.\n\n"
                "To install manually:\n"
                "1. Open QGIS Python Console (Ctrl+Alt+P or Cmd+Alt+P)\n"
                "2. Run:\n"
                "   import subprocess, sys, os\n"
                "   python_exe = os.path.join(sys.prefix, 'bin', 'python3')\n"
                "   subprocess.run([python_exe, '-m', 'pip', 'install', '--user', 'pandas', 'scipy', 'numpy', 'matplotlib'])\n"
                "3. Restart QGIS"
            )
            return False
        
        # User agreed, try to install
        QMessageBox.information(
            iface.mainWindow(),
            "STAR-BME: Installing Dependencies",
            "Installing packages... This may take a few minutes.\n\n"
            "QGIS may appear frozen during installation.\n"
            "Please wait..."
        )
        
        # Try installation
        success, message = installer.install_dependencies()
        
        if success:
            QMessageBox.information(
                iface.mainWindow(),
                "STAR-BME: Installation Successful",
                f"{message}\n\n"
                "Please restart QGIS to use the plugin."
            )
            return False  # Return False to prevent loading before restart
        else:
            QMessageBox.critical(
                iface.mainWindow(),
                "STAR-BME: Installation Failed",
                message
            )
            return False
    else:
        # No interface available (shouldn't happen in normal usage)
        print(f"[STAR_BME] Missing dependencies: {', '.join(installer.missing_packages)}")
        return False


def check_dependencies_silent():
    """
    Silently check if dependencies are available (no GUI)
    
    Returns:
        bool: True if all dependencies available
    """
    installer = DependencyInstaller()
    return installer.check_dependencies()


if __name__ == "__main__":
    # Allow testing from command line
    installer = DependencyInstaller()
    
    print("Checking dependencies...")
    if installer.check_dependencies():
        print("✅ All dependencies available!")
    else:
        print(f"❌ Missing: {', '.join(installer.missing_packages)}")
        print("\nAttempting installation...")
        success, message = installer.install_dependencies()
        print(message)
