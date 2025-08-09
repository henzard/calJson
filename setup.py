"""
Setup script for Weight Certificate PDF to JSON Converter
========================================================
This script helps set up the environment and dependencies.
"""

import subprocess
import sys
import platform
import os
from pathlib import Path

def run_command(command, shell=False):
    """Run a system command and return the result."""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def install_python_dependencies():
    """Install Python dependencies from requirements.txt."""
    print("\n📦 Installing Python dependencies...")
    
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    success, stdout, stderr = run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    if success:
        print("✅ Python dependencies installed successfully")
        return True
    else:
        print(f"❌ Failed to install dependencies: {stderr}")
        return False

def check_tesseract():
    """Check if Tesseract OCR is installed."""
    print("\n🔍 Checking for Tesseract OCR...")
    
    success, stdout, stderr = run_command(["tesseract", "--version"])
    
    if success:
        version_line = stdout.split('\n')[0]
        print(f"✅ Tesseract found: {version_line}")
        return True
    else:
        print("❌ Tesseract OCR not found")
        print_tesseract_install_instructions()
        return False

def check_poppler():
    """Check if Poppler utilities are installed."""
    print("\n🔍 Checking for Poppler utilities...")
    
    # Try different command names based on OS
    commands_to_try = ["pdftoppm", "pdfinfo"]
    
    for cmd in commands_to_try:
        success, stdout, stderr = run_command([cmd, "-v"])
        if success:
            print(f"✅ Poppler found: {cmd} available")
            return True
    
    print("❌ Poppler utilities not found")
    print_poppler_install_instructions()
    return False

def print_tesseract_install_instructions():
    """Print OS-specific instructions for installing Tesseract."""
    os_name = platform.system().lower()
    
    print("\n📋 Tesseract OCR Installation Instructions:")
    
    if os_name == "windows":
        print("   Windows:")
        print("   1. Run: winget install UB-Mannheim.TesseractOCR")
        print("   2. Or download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   3. Add to your system PATH")
    
    elif os_name == "darwin":  # macOS
        print("   macOS:")
        print("   1. Install Homebrew if not already installed")
        print("   2. Run: brew install tesseract")
    
    else:  # Linux
        print("   Ubuntu/Debian:")
        print("   1. Run: sudo apt update")
        print("   2. Run: sudo apt install tesseract-ocr")
        print("")
        print("   CentOS/RHEL:")
        print("   1. Run: sudo yum install tesseract")

def print_poppler_install_instructions():
    """Print OS-specific instructions for installing Poppler."""
    os_name = platform.system().lower()
    
    print("\n📋 Poppler Installation Instructions:")
    
    if os_name == "windows":
        print("   Windows:")
        print("   1. Download from: https://github.com/oschwartz10612/poppler-windows/releases")
        print("   2. Extract to a folder (e.g., C:\\poppler)")
        print("   3. Add the bin folder to your system PATH")
        print("   4. Or set POPPLER_PATH environment variable")
    
    elif os_name == "darwin":  # macOS
        print("   macOS:")
        print("   1. Install Homebrew if not already installed")
        print("   2. Run: brew install poppler")
    
    else:  # Linux
        print("   Ubuntu/Debian:")
        print("   1. Run: sudo apt update")
        print("   2. Run: sudo apt install poppler-utils")
        print("")
        print("   CentOS/RHEL:")
        print("   1. Run: sudo yum install poppler-utils")

def test_installation():
    """Test if the installation is working correctly."""
    print("\n🧪 Testing installation...")
    
    try:
        # Test imports
        import streamlit
        import pdf2image
        import PIL
        import pytesseract
        import jsonschema
        
        print("✅ All Python packages imported successfully")
        
        # Test Tesseract
        try:
            from pytesseract import pytesseract
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract integration working: {version}")
        except Exception as e:
            print(f"❌ Tesseract integration failed: {e}")
            return False
        
        print("✅ Installation test passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Weight Certificate PDF to JSON Converter Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install Python dependencies
    if not install_python_dependencies():
        print("\n❌ Setup failed: Could not install Python dependencies")
        return
    
    # Check system dependencies
    tesseract_ok = check_tesseract()
    poppler_ok = check_poppler()
    
    if not tesseract_ok or not poppler_ok:
        print(f"\n⚠️  Setup incomplete: Missing system dependencies")
        print("   Please install the missing dependencies and run setup again")
        return
    
    # Test installation
    if test_installation():
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run: streamlit run app.py")
        print("2. Open your browser to http://localhost:8501")
        print("3. Upload a PDF weight certificate and start converting!")
    else:
        print("\n❌ Setup completed with errors")
        print("   Please check the error messages above and resolve any issues")

if __name__ == "__main__":
    main()
