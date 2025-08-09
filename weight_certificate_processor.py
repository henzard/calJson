"""
Weight Certificate OCR Processor
================================
Processes weight certificate PDFs and extracts structured data to JSON.

Based on the CM-25-181B certificate processing script.
Converts PDF pages to images, performs OCR, and extracts weight table data.
"""

import re
import os
import json
import tempfile
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Tesseract path for Windows and Linux/Cloud
def setup_tesseract():
    """Set up Tesseract OCR path for Windows and cloud environments."""
    # For cloud/Linux environments, try default first
    try:
        pytesseract.get_tesseract_version()
        logger.info("Using system Tesseract (default path)")
        return  # Already working
    except:
        pass
    
    # Windows-specific paths
    possible_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    for path in possible_tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Using Tesseract from: {path}")
            return
    
    logger.warning("Tesseract not found in common locations")

# Set up Tesseract on import
setup_tesseract()

class WeightCertificateProcessor:
    """
    Processes weight certificate PDFs and converts them to structured JSON.
    
    Handles:
    - Multi-page PDF conversion to images
    - OCR text extraction
    - Weight table parsing
    - JSON schema validation (optional)
    """
    
    def __init__(self, pdf_path: str, schema_path: Optional[str] = None, 
                 dpi: int = 180, cache_dir: Optional[str] = None):
        """
        Initialize the processor.
        
        Args:
            pdf_path: Path to the PDF file to process
            schema_path: Optional path to JSON schema for validation
            dpi: DPI for PDF to image conversion (higher = better quality, slower)
            cache_dir: Directory to cache converted images (None = no caching)
        """
        self.pdf_path = Path(pdf_path)
        self.schema_path = Path(schema_path) if schema_path else None
        self.dpi = dpi
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.validation_passed = False
        self.processing_timestamp = datetime.now().isoformat()
        
        # Create cache directory if specified
        if self.cache_dir:
            self.cache_dir.mkdir(exist_ok=True)
            
        # Verify PDF exists
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
    
    def get_processing_timestamp(self) -> str:
        """Get the processing timestamp."""
        return self.processing_timestamp
    
    def get_page_image(self, page_no: int) -> Image.Image:
        """
        Get a PIL image for the specified page number.
        
        Args:
            page_no: Page number (1-indexed)
            
        Returns:
            PIL Image object
        """
        # Check cache first if caching is enabled
        if self.cache_dir:
            png_path = self.cache_dir / f"page_{page_no}.png"
            if png_path.exists():
                logger.info(f"Loading cached page {page_no}")
                return Image.open(png_path)
        
        # Convert PDF page to image
        logger.info(f"Converting PDF page {page_no} to image")
        try:
            # Set poppler path - check multiple possible locations
            poppler_path = None
            possible_paths = [
                # Cloud/Linux default (usually in PATH)
                None,  # Let pdf2image auto-detect
                # Windows specific paths
                r"C:\Project\calJson\poppler-24.08.0\Library\bin",
                r"C:\poppler\bin",
                # Environment variable
                os.environ.get("POPPLER_PATH")
            ]
            
            for path in possible_paths:
                if path is None:
                    # Try without specifying path (cloud/Linux default)
                    poppler_path = None
                    logger.info("Using system Poppler (default path)")
                    break
                elif path and os.path.exists(path):
                    poppler_path = path
                    logger.info(f"Using Poppler from: {poppler_path}")
                    break
            
            pages = convert_from_path(
                self.pdf_path, 
                dpi=self.dpi,
                first_page=page_no, 
                last_page=page_no,
                poppler_path=poppler_path
            )
        except Exception as e:
            if "poppler" in str(e).lower():
                raise RuntimeError(
                    f"Poppler utilities not found. Please install Poppler:\n"
                    f"1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/latest\n"
                    f"2. Extract to C:\\poppler\n"
                    f"3. Add C:\\poppler\\bin to your system PATH\n"
                    f"Original error: {e}"
                )
            else:
                raise e
        
        if not pages:
            raise ValueError(f"Could not convert page {page_no}")
            
        page_image = pages[0]
        
        # Save to cache if caching is enabled
        if self.cache_dir:
            png_path = self.cache_dir / f"page_{page_no}.png"
            page_image.save(png_path)
            logger.info(f"Cached page {page_no} to {png_path}")
        
        return page_image
    
    def extract_metadata(self, page_image: Image.Image) -> Dict[str, Any]:
        """
        Extract certificate metadata from the first page.
        
        Args:
            page_image: PIL Image of the first page
            
        Returns:
            Dictionary containing metadata fields
        """
        logger.info("Extracting metadata from page 1")
        
        # Perform OCR on the page
        meta_text = pytesseract.image_to_string(page_image)
        
        def grab_pattern(pattern: str, default: str = "") -> str:
            """Helper to extract text using regex pattern."""
            match = re.search(pattern, meta_text, re.I)
            return match.group(1).strip() if match else default
        
        # Extract metadata fields
        metadata = {
            "certificate_number": grab_pattern(r"Certificate\s+No\.\s*([A-Z0-9/ -]+)"),
            "title": "ON-SITE CALIBRATION CERTIFICATE",
            "pages": 12,  # Default for CM-25-181B type certificates
            "issuing_lab": grab_pattern(r"(\bCM LAB.*)", "CM LAB (Pty) Ltd"),
            "accreditation_body": "SANAS",
            "date_issued": grab_pattern(r"Date of Issue:\s*([0-9-]+)"),
            "date_expiry": grab_pattern(r"Date of Expiry:\s*([0-9-]+)"),
            "calibration_dates": re.findall(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", meta_text),
            "customer_name": grab_pattern(r"Calibration of:\s*([\w ].+?)\s*(?:Calibration Date|$)"),
            "site_address": "c/o Vlei & John Mitten St, Douglas Valley SH, Deaglesgift, Bloemfontein",
            "contact_person": grab_pattern(r"Contact details:\s*([A-Za-z ].+?)(?:[0-9]|$)"),
        }
        
        logger.info(f"Extracted metadata: {metadata['certificate_number']}")
        return metadata
    
    def extract_weights_and_sets(self, start_page: int = 2, end_page: int = 12) -> tuple[List[Dict], List[Dict]]:
        """
        Extract weight data from the specified page range.
        
        Args:
            start_page: First page to process (inclusive)
            end_page: Last page to process (inclusive)
            
        Returns:
            Tuple of (weights_list, sets_list)
        """
        logger.info(f"Extracting weights from pages {start_page}-{end_page}")
        
        weights = []
        sets = []
        current_set = None
        
        # Regex patterns for different types of data
        table_line_pattern = re.compile(r'^(W[FE]S)\s*(\d+).+?20\s*000.*?([\d.,]+)\s+([0-9][.,][0-9]+)$')
        set_header_pattern = re.compile(r'Set\s+No\.?\s*W(\d)', re.I)
        
        for page_num in range(start_page, end_page + 1):
            logger.info(f"Processing page {page_num}")
            
            # Get page image and extract text
            page_image = self.get_page_image(page_num)
            page_text = pytesseract.image_to_string(page_image).replace("\xa0", " ")
            
            # Process each line
            for raw_line in page_text.splitlines():
                line = re.sub(r'\s+', ' ', raw_line.strip())
                if not line:
                    continue
                
                # Check for full weight set rows (pages 2-8, typically 20kg weights)
                table_match = table_line_pattern.match(line)
                if table_match:
                    prefix, num, after_value, uncertainty = table_match.groups()
                    weight_id = f"{prefix}{num}"
                    
                    try:
                        # Parse numeric values (handle different decimal separators)
                        # Clean and validate before conversion
                        after_clean = after_value.strip()
                        uncertainty_clean = uncertainty.strip()
                        
                        # Skip if empty or just punctuation
                        if not after_clean or after_clean in ['.', ','] or not uncertainty_clean or uncertainty_clean in ['.', ',']:
                            logger.warning(f"Skipping invalid numeric values: '{after_value}', '{uncertainty}'")
                            continue
                            
                        # Handle European vs US number formats
                        if ',' in after_clean and '.' in after_clean:
                            # Format like 20.000,12 (European)
                            actual_after = float(after_clean.replace('.', '').replace(',', '.'))
                        elif ',' in after_clean:
                            # Format like 20000,12 (European decimal)
                            actual_after = float(after_clean.replace(',', '.'))
                        else:
                            # Format like 20000.12 (US)
                            actual_after = float(after_clean)
                        
                        uncertainty_val = float(uncertainty_clean.replace(',', '.'))
                        
                        weights.append({
                            "weight_id": weight_id,
                            "nominal": 20000,  # 20kg weights
                            "actual_after": actual_after,
                            "uncertainty": uncertainty_val,
                        })
                        
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Could not parse weight values from line: {line} - {e}")
                        continue
                    continue
                
                # Check for small weight set headers (pages 9-12)
                set_header_match = set_header_pattern.search(line)
                if set_header_match:
                    set_number = set_header_match.group(1)
                    current_set = {
                        "id": f"W{set_number}",
                        "weights": []
                    }
                    sets.append(current_set)
                    logger.info(f"Found weight set: W{set_number}")
                    continue
                
                # Check for small weight set data rows
                if current_set:
                    # Extract numeric values from the line
                    numbers = re.findall(r'[0-9]+(?:[.,][0-9]+)?', line)
                    
                    if len(numbers) >= 3:  # Need at least nominal, actual, uncertainty
                        try:
                            # Clean and validate numbers
                            clean_numbers = []
                            for num in numbers[:3]:  # Only take first 3 numbers
                                if not num or num in ['.', ',']:
                                    continue
                                clean_numbers.append(num)
                            
                            if len(clean_numbers) < 3:
                                logger.warning(f"Insufficient valid numbers in line: {line}")
                                continue
                            
                            # Parse values (handle different decimal formats)
                            def parse_number(num_str, is_weight=False):
                                """Parse number handling different decimal formats"""
                                num_str = num_str.strip()
                                if ',' in num_str and '.' in num_str:
                                    # European format: 1.000,50
                                    if is_weight:
                                        return float(num_str.replace('.', '').replace(',', '.'))
                                    else:
                                        return float(num_str.replace('.', '').replace(',', '.'))
                                elif ',' in num_str:
                                    # Decimal comma: 1000,50
                                    return float(num_str.replace(',', '.'))
                                else:
                                    # Standard format: 1000.50
                                    return float(num_str)
                            
                            nominal = parse_number(clean_numbers[0], is_weight=True)
                            actual_after = parse_number(clean_numbers[1])
                            uncertainty_val = parse_number(clean_numbers[2])
                            
                            # Generate weight ID
                            weight_id = f"{current_set['id']}-{int(nominal)}"
                            
                            current_set["weights"].append({
                                "weight_id": weight_id,
                                "nominal": nominal,
                                "actual_after": actual_after,
                                "uncertainty": uncertainty_val
                            })
                            
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Could not parse weight data from line: {line} - {e}")
                            continue
        
        logger.info(f"Extracted {len(weights)} individual weights and {len(sets)} weight sets")
        return weights, sets
    
    def validate_json(self, data: Dict[str, Any]) -> bool:
        """
        Validate the extracted data against the JSON schema.
        
        Args:
            data: The extracted certificate data
            
        Returns:
            True if validation passes, False otherwise
        """
        if not self.schema_path or not self.schema_path.exists():
            logger.info("No schema provided or schema file not found - skipping validation")
            return True
        
        try:
            from jsonschema import validate
            
            logger.info(f"Validating against schema: {self.schema_path}")
            
            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
            
            validate(instance=data, schema=schema)
            logger.info("✅ JSON validation passed")
            self.validation_passed = True
            return True
            
        except ImportError:
            logger.warning("jsonschema package not available - skipping validation")
            return True
            
        except Exception as e:
            logger.error(f"❌ JSON validation failed: {e}")
            self.validation_passed = False
            return False
    
    def process(self) -> Dict[str, Any]:
        """
        Main processing method - converts PDF to structured JSON.
        
        Returns:
            Dictionary containing the complete certificate data
        """
        logger.info(f"Starting processing of {self.pdf_path}")
        
        # Step 1: Extract metadata from first page
        page1_image = self.get_page_image(1)
        metadata = self.extract_metadata(page1_image)
        
        # Step 2: Extract weights and sets from remaining pages
        weights, sets = self.extract_weights_and_sets()
        
        # Step 3: Build complete certificate data
        certificate_data = {
            **metadata,
            "weights": weights,
            "sets": sets
        }
        
        # Step 4: Validate against schema if provided
        self.validate_json(certificate_data)
        
        logger.info("✅ Processing completed successfully")
        logger.info(f"Result: {len(weights)} weights, {len(sets)} sets")
        
        return certificate_data
    
    def save_json(self, output_path: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Save the processed data to a JSON file.
        
        Args:
            output_path: Path where to save the JSON file
            data: Data to save (if None, will process the PDF first)
            
        Returns:
            Path to the saved file
        """
        if data is None:
            data = self.process()
        
        output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved JSON to {output_path}")
        return str(output_path)


def main():
    """
    Command-line interface for the weight certificate processor.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert weight certificate PDF to JSON")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("-s", "--schema", help="JSON schema file for validation")
    parser.add_argument("--dpi", type=int, default=180, help="DPI for image conversion")
    parser.add_argument("--cache", help="Directory for caching converted images")
    
    args = parser.parse_args()
    
    # Set output path if not provided
    if not args.output:
        pdf_path = Path(args.pdf_path)
        args.output = pdf_path.stem + "_converted.json"
    
    # Process the PDF
    processor = WeightCertificateProcessor(
        pdf_path=args.pdf_path,
        schema_path=args.schema,
        dpi=args.dpi,
        cache_dir=args.cache
    )
    
    result = processor.process()
    processor.save_json(args.output, result)
    
    print(f"✅ Conversion completed!")
    print(f"   Input: {args.pdf_path}")
    print(f"   Output: {args.output}")
    print(f"   Weights: {len(result.get('weights', []))}")
    print(f"   Sets: {len(result.get('sets', []))}")


if __name__ == "__main__":
    main()
