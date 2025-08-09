"""
Streamlit App for PDF to JSON Weight Certificate Conversion
===========================================================
Upload a PDF weight certificate and get back a structured JSON file.
"""

import streamlit as st
import tempfile
import os
import json
from pathlib import Path
import zipfile
import io
from weight_certificate_processor import WeightCertificateProcessor

# Configure Streamlit page
st.set_page_config(
    page_title="Weight Certificate PDF to JSON Converter",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📋 Weight Certificate PDF to JSON Converter")
    
    # Sidebar with information
    with st.sidebar:
        st.header("📖 How to Use")
        st.markdown("""
        1. **Upload PDF**: Select your weight certificate PDF file
        2. **Optional Schema**: Upload a JSON schema for validation
        3. **Process**: Click 'Convert to JSON' to start processing
        4. **Download**: Get your structured JSON file
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 File Upload")
        
        # PDF file upload
        uploaded_pdf = st.file_uploader(
            "Choose a PDF weight certificate file",
            type=['pdf'],
            help="Upload a weight certificate PDF file for conversion to JSON"
        )
        
        # Optional schema upload
        uploaded_schema = st.file_uploader(
            "Optional: Upload JSON schema for validation",
            type=['json'],
            help="Upload a JSON schema file to validate the output against"
        )
        
        # Processing options
        st.header("⚙️ Processing Options")
        
        dpi = st.slider("OCR DPI Quality", min_value=150, max_value=300, value=180, step=10)
        cache_images = st.checkbox("Cache converted images", value=True)
        
        # Process button
        if uploaded_pdf is not None:
            if st.button("🚀 Convert to JSON", type="primary"):
                process_pdf(uploaded_pdf, uploaded_schema, dpi, cache_images)
    
    with col2:
        st.header("📊 Status")
        
        if 'processing_status' not in st.session_state:
            st.session_state.processing_status = "Ready to process"
        
        st.info(f"Status: {st.session_state.processing_status}")
        
        # Results area
        if 'json_result' in st.session_state:
            st.header("📥 Download Results")
            
            st.download_button(
                label="📄 Download JSON",
                data=st.session_state.json_result,
                file_name=f"{st.session_state.output_filename}.json",
                mime="application/json"
            )

def process_pdf(uploaded_pdf, uploaded_schema, dpi, cache_images):
    """Process the uploaded PDF and convert to JSON."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        st.session_state.processing_status = "Processing..."
        status_text.text("🔄 Processing PDF...")
        progress_bar.progress(20)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded PDF
            pdf_path = temp_path / uploaded_pdf.name
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_pdf.getbuffer())
            
            progress_bar.progress(40)
            
            # Save schema if provided
            schema_path = None
            if uploaded_schema is not None:
                schema_path = temp_path / uploaded_schema.name
                with open(schema_path, 'w') as f:
                    f.write(uploaded_schema.getvalue().decode('utf-8'))
            
            # Initialize processor
            processor = WeightCertificateProcessor(
                pdf_path=str(pdf_path),
                schema_path=str(schema_path) if schema_path else None,
                dpi=dpi,
                cache_dir=str(temp_path / "_page_cache") if cache_images else None
            )
            
            progress_bar.progress(60)
            
            # Process the PDF
            result = processor.process()
            
            progress_bar.progress(80)
            
            # Generate output filename
            base_name = Path(uploaded_pdf.name).stem
            output_filename = f"{base_name}_converted"
            
            # Store results in session state
            st.session_state.json_result = json.dumps(result, indent=2)
            st.session_state.output_filename = output_filename
            
            progress_bar.progress(100)
            status_text.text("✅ Processing completed!")
            
            st.session_state.processing_status = "Completed successfully"
            st.success(f"Successfully processed {uploaded_pdf.name}!")
            
    except Exception as e:
        st.session_state.processing_status = f"Error: {str(e)}"
        progress_bar.progress(0)
        status_text.text("❌ Processing failed")
        st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
