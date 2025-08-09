# Weight Certificate PDF to JSON Converter

A Streamlit web application that converts weight certificate PDFs (like CM-25-181B) into structured JSON format using OCR technology.

## Features

- 🔄 **PDF to JSON Conversion**: Upload PDF weight certificates and get structured JSON output
- 📋 **OCR Processing**: Automatic text extraction from scanned documents
- ✅ **Schema Validation**: Optional JSON schema validation for data integrity
- 🎯 **Weight Table Detection**: Intelligent parsing of weight tables and measurement data
- 📱 **User-friendly Interface**: Clean, responsive Streamlit web interface
- 💾 **Batch Downloads**: Download individual JSON files or complete ZIP packages
- ⚡ **Image Caching**: Optional caching for faster reprocessing

## Quick Start

### Prerequisites

Before running the application, you need to install external dependencies:

#### Windows
```bash
# Install Tesseract OCR
winget install UB-Mannheim.TesseractOCR

# Install Poppler for PDF processing
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Extract and add to your PATH
```

#### macOS
```bash
# Install using Homebrew
brew install tesseract poppler
```

#### Ubuntu/Debian
```bash
# Install required packages
sudo apt update
sudo apt install tesseract-ocr poppler-utils
```

### Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd calJson
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit application**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser** to `http://localhost:8501`

## Usage

### Web Interface

1. **Upload PDF**: Select your weight certificate PDF file
2. **Optional Schema**: Upload a JSON schema file for validation (optional)
3. **Configure Options**:
   - Adjust OCR DPI quality (higher = better quality, slower processing)
   - Enable/disable image caching for faster reprocessing
4. **Process**: Click "Convert to JSON" to start processing
5. **Download**: Get your structured JSON file or complete ZIP package

### Command Line Interface

You can also use the processor directly from the command line:

```bash
# Basic usage
python weight_certificate_processor.py certificate.pdf

# With custom output file
python weight_certificate_processor.py certificate.pdf -o output.json

# With schema validation
python weight_certificate_processor.py certificate.pdf -s schema.json

# With custom DPI and caching
python weight_certificate_processor.py certificate.pdf --dpi 300 --cache ./cache
```

## Supported Document Types

The application is optimized for weight certificate documents similar to CM-25-181B format:

- **Multi-page PDFs** (typically 12 pages)
- **Weight tables** with nominal, actual, and uncertainty values
- **Individual weights** (e.g., 20kg weights with IDs like WFS001, WES123)
- **Weight sets** (smaller weights grouped in sets W1-W9)
- **Certificate metadata** (dates, customer info, lab details)

## Output Format

The generated JSON follows this structure:

```json
{
  "certificate_number": "CM 25 181B",
  "title": "ON-SITE CALIBRATION CERTIFICATE",
  "pages": 12,
  "issuing_lab": "CM LAB (Pty) Ltd",
  "date_issued": "2024-01-15",
  "date_expiry": "2025-01-15",
  "customer_name": "Example Customer",
  "weights": [
    {
      "weight_id": "WFS001",
      "nominal": 20000,
      "actual_after": 20000.12,
      "uncertainty": 0.15
    }
  ],
  "sets": [
    {
      "id": "W1",
      "weights": [
        {
          "weight_id": "W1-500",
          "nominal": 500,
          "actual_after": 500.02,
          "uncertainty": 0.05
        }
      ]
    }
  ]
}
```

## Configuration Options

### Processing Options

- **DPI Quality**: Controls image conversion quality (150-300)
  - 150: Fast processing, lower accuracy
  - 180: Balanced (default)
  - 300: High accuracy, slower processing

- **Image Caching**: Enables caching of converted PDF pages
  - Speeds up reprocessing of the same document
  - Useful for testing and development

### Schema Validation

Upload a JSON schema file to validate the output structure. The application includes a default schema (`weight_certificate_import_schema.json`) that validates:

- Required fields presence
- Data types and formats
- Value ranges and patterns
- Weight ID format validation

## File Structure

```
calJson/
├── app.py                                    # Main Streamlit application
├── weight_certificate_processor.py          # OCR processing module
├── weight_certificate_import_schema.json    # JSON validation schema
├── requirements.txt                          # Python dependencies
└── README.md                                # This file
```

## Troubleshooting

### Common Issues

**1. Tesseract not found**
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```
- **Solution**: Install Tesseract OCR and ensure it's in your system PATH

**2. Poppler not found**
```
PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?
```
- **Solution**: Install Poppler utilities and add to PATH

**3. Poor OCR accuracy**
- Try increasing the DPI setting
- Ensure the PDF has good image quality
- Check if the document is rotated or skewed

**4. Missing weights or data**
- Verify the document follows the expected format
- Check OCR output in debug mode
- Adjust regex patterns in the processor if needed

### Performance Tips

- Use image caching for repeated processing of the same document
- Start with lower DPI (150-180) for initial testing
- Process documents in smaller batches for large volumes

## Dependencies

### Python Packages
- `streamlit` - Web application framework
- `pdf2image` - PDF to image conversion
- `Pillow` - Image processing
- `pytesseract` - OCR engine wrapper
- `jsonschema` - JSON validation

### System Dependencies
- **Tesseract OCR** - Text recognition engine
- **Poppler** - PDF processing utilities

## Development

### Adding New Document Types

To support additional weight certificate formats:

1. Extend the regex patterns in `weight_certificate_processor.py`
2. Modify the `extract_metadata()` method for new field extraction
3. Update the `extract_weights_and_sets()` method for new table formats
4. Adjust the JSON schema as needed

### Customizing the Interface

The Streamlit interface can be customized by modifying `app.py`:
- Change styling in the CSS section
- Add new processing options
- Modify the layout and components

## License

This project is provided as-is for educational and commercial use. Please ensure compliance with any applicable regulations when processing sensitive calibration data.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify all dependencies are properly installed
3. Test with the provided sample schema
4. Review the console logs for error details

## Version History

- **v1.0.0** - Initial release with CM-25-181B support
  - Streamlit web interface
  - OCR processing with caching
  - JSON schema validation
  - Batch download functionality
