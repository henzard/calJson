# Manual Poppler Installation for Windows

## Quick Setup Instructions

1. **Download Poppler**:
   - Visit: https://github.com/oschwartz10612/poppler-windows/releases/latest
   - Download the latest ZIP file (e.g., `Release-24.08.0-0.zip`)

2. **Extract Files**:
   - Create folder: `C:\poppler`
   - Extract the downloaded ZIP to `C:\poppler`
   - Your folder structure should look like:
     ```
     C:\poppler\
     ├── bin\
     │   ├── pdfinfo.exe
     │   ├── pdftoppm.exe
     │   └── ... (other executables)
     ├── include\
     └── ... (other folders)
     ```

3. **Add to PATH**:
   - Open "Environment Variables" in Windows
   - Edit the "Path" variable for your user
   - Add: `C:\poppler\bin`
   - Click OK to save

4. **Verify Installation**:
   - Open a new PowerShell/Command Prompt
   - Run: `pdfinfo -v`
   - You should see version information

## Alternative: Quick PowerShell Setup

Run this in PowerShell (as Administrator if needed):

```powershell
# Create directory
New-Item -ItemType Directory -Path "C:\poppler" -Force

# Download (you'll need to manually download and extract)
Write-Host "Please download from: https://github.com/oschwartz10612/poppler-windows/releases/latest"
Write-Host "Extract to: C:\poppler"

# Add to PATH (run after extracting)
$currentPath = [Environment]::GetEnvironmentVariable("PATH", [EnvironmentVariableTarget]::User)
if ($currentPath -notlike "*C:\poppler\bin*") {
    $newPath = "$currentPath;C:\poppler\bin"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, [EnvironmentVariableTarget]::User)
    Write-Host "Added C:\poppler\bin to PATH"
}
```

## Test After Installation

Run this in your project directory:
```powershell
python test_dependencies.py
```

This will verify both Tesseract and Poppler are working correctly.
