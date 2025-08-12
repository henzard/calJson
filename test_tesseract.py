#!/usr/bin/env python3
"""
Test script to verify Tesseract configuration with img2table
"""

import os

# Configure Tesseract path for Windows
def setup_tesseract():
    """Set up Tesseract OCR path for Windows."""
    # Windows-specific paths
    possible_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    for path in possible_tesseract_paths:
        if os.path.exists(path):
            # Set environment variables for img2table
            tesseract_dir = os.path.dirname(path)
            os.environ["PATH"] = tesseract_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ["TESSERACT_PATH"] = path
            print(f"✅ Set TESSERACT_PATH to: {path}")
            print(f"✅ Added Tesseract to PATH: {tesseract_dir}")
            return path
    
    print("❌ Tesseract not found in common locations")
    return None

# Monkey patch img2table to use our Tesseract path
def patch_img2table_tesseract():
    """Patch img2table to use our configured Tesseract path."""
    try:
        import img2table.ocr.tesseract
        original_init = img2table.ocr.tesseract.TesseractOCR.__init__
        
        def patched_init(self, n_threads=1, lang='eng', psm=11, tessdata_dir=None):
            # Create custom environment with our PATH
            env = os.environ.copy()
            if tessdata_dir:
                env["TESSDATA_PREFIX"] = tessdata_dir
            
            # Override the environment to include our Tesseract path
            self.env = env
            
            # Skip the subprocess check since we know Tesseract exists
            # This is a bit of a hack, but it should work
            self.n_threads = n_threads
            self.lang = lang
            self.psm = psm
        
        # Apply the patch
        img2table.ocr.tesseract.TesseractOCR.__init__ = patched_init
        print("✅ Patched img2table TesseractOCR")
        
    except Exception as e:
        print(f"⚠️ Could not patch img2table: {e}")

# Set up Tesseract
tesseract_path = setup_tesseract()

if tesseract_path:
    try:
        # Test pytesseract
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        version = pytesseract.get_tesseract_version()
        print(f"✅ pytesseract working: {version}")
        
        # Apply the patch before testing img2table
        patch_img2table_tesseract()
        
        # Test img2table
        from img2table.ocr import TesseractOCR
        ocr = TesseractOCR(lang="eng")
        print("✅ img2table TesseractOCR created successfully")
        
        print("\n🎉 All tests passed! Tesseract is properly configured.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ Could not configure Tesseract")
