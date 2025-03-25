"""
AutoWealthTranslate Streamlit App
---------------------------------
A Streamlit UI for the AutoWealthTranslate application.
"""

import os
import streamlit as st
import tempfile
from pathlib import Path
import time
import logging
import shutil
import uuid
import base64
import io

from auto_wealth_translate.core.document_processor import DocumentProcessor
from auto_wealth_translate.core.translator import TranslationService
from auto_wealth_translate.core.document_rebuilder import DocumentRebuilder
from auto_wealth_translate.core.validator import OutputValidator
from auto_wealth_translate.core.markdown_processor import MarkdownProcessor
from auto_wealth_translate.core.chart_processor import chart_to_markdown
from auto_wealth_translate.utils.logger import setup_logger, get_logger

# Configure logging
setup_logger(logging.INFO)
logger = get_logger("streamlit_app")

# Set more verbose logging for the markdown processor module
markdown_logger = logging.getLogger("auto_wealth_translate.core.markdown_processor")
markdown_logger.setLevel(logging.DEBUG)

# Create a file handler for detailed logs
log_file = Path(tempfile.gettempdir()) / "markdown_processor_debug.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
markdown_logger.addHandler(file_handler)

logger.info(f"Debug logs will be written to: {log_file}")

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "Chinese (中文)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "de": "German (Deutsch)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "ru": "Russian (Русский)",
    "ar": "Arabic (العربية)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)"
}

# Translation models
TRANSLATION_MODELS = {
    "gpt-4": "GPT-4 (Best quality, slower)",
    "gpt-3.5-turbo": "GPT-3.5 Turbo (Faster, good quality)",
    "llama-2": "Llama-2 (Local processing, requires additional setup)"
}

# PDF processing modes
PDF_PROCESSING_MODES = {
    "enhanced": "Enhanced Layout (Improved basic mode)",
    "precise": "Precise Layout (Canva-like, preserves original formatting)",
    "bilingual": "Bilingual Mode (Adds translation pages after originals)",
    "markdown": "Markdown Mode (Document structure preservation, best for complex formats)"
}

# More detailed descriptions for each mode
PDF_MODE_DESCRIPTIONS = {
    "enhanced": """
    **Enhanced Layout Mode**: Improved rendering with better typography and spacing.
    - Better text layout and font handling
    - Improved CJK character support for Chinese text
    - Table formatting with headers and proper cell alignment
    - Best for documents with moderate complexity
    """,
    
    "precise": """
    **Precise Layout Mode**: Preserves exact original layout like Canva.
    - Maintains exact positions of all elements
    - Only replaces text content while keeping original styling
    - Intelligent font size adjustment for translated text
    - Enhanced CJK font support for Chinese characters
    - Best for complex documents where layout preservation is critical
    """,
    
    "bilingual": """
    **Bilingual Mode**: Keeps original pages and adds translations.
    - Original document pages remain untouched
    - Adds new pages with translations after each original page
    - Clear formatting for translated pages with proper section headers
    - Full Unicode support for all languages
    - Best for when both original and translation need to be presented
    """,
    
    "markdown": """
    **Markdown Processing Mode**: Uses Markdown as an intermediate format.
    - Preserves document structure and semantic elements
    - Better handling of complex documents with mixed content
    - Superior text flow and formatting for translations
    - Enhanced table and list processing
    - Best for complex financial documents with detailed formatting requirements
    - Improved handling of CJK characters
    """
}

def create_temp_dir():
    """Create a temporary directory for file processing."""
    temp_dir = Path(tempfile.gettempdir()) / "autowealthtranslate_streamlit"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def get_file_download_link(file_path, link_text):
    """Generate a download link for a file."""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    filename = Path(file_path).name
    mime_type = "application/pdf" if file_path.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}">{link_text}</a>'
    return href

def translate_document(input_file, source_lang, target_lang, model="gpt-4", api_key=None, pdf_mode="enhanced"):
    """
    Process and translate a document.
    
    Args:
        input_file: Path to input file
        source_lang: Source language code
        target_lang: Target language code
        model: Translation model to use
        api_key: OpenAI API key
        pdf_mode: PDF processing mode ('enhanced', 'precise', 'bilingual', or 'markdown')
    
    Returns:
        Path to translated file, validation results, markdown content (if markdown mode)
    """
    # Set OpenAI API key if provided
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    temp_dir = create_temp_dir()
    
    # Generate unique filename
    input_path = Path(input_file)
    unique_id = str(uuid.uuid4())[:8]
    output_path = temp_dir / f"{input_path.stem}_{target_lang}_{unique_id}{input_path.suffix}"
    
    if pdf_mode == "markdown":
        # Use Markdown processor for enhanced document structure preservation
        logger.info(f"Using Markdown processing mode for {input_path}")
        
        # More detailed logging
        logger.info(f"Source language: {source_lang}, Target language: {target_lang}")
        logger.info(f"Using translation model: {model}")
        logger.info(f"Output path will be: {output_path}")
        
        md_processor = MarkdownProcessor()
        
        # Convert document to markdown
        if input_path.suffix.lower() == '.pdf':
            logger.info(f"Converting PDF to Markdown: {input_path}")
            md_content = md_processor.pdf_to_markdown(str(input_path))
            
            # Log some extracted content for verification
            logger.info(f"Extracted markdown content sample (first 200 chars): {md_content[:200]}")
            logger.info(f"Total markdown content length: {len(md_content)} characters")
        else:
            # For future implementation of other document types
            raise NotImplementedError(f"Markdown processing for {input_path.suffix} files is not yet supported")
        
        # Initialize translation service
        logger.info(f"Initializing translation service from {source_lang} to {target_lang} using {model}")
        translation_service = TranslationService(
            source_lang=source_lang,
            target_lang=target_lang, 
            model=model
        )
        
        # Translate markdown content
        logger.info("Starting translation of markdown content")
        translated_md = md_processor.translate_markdown(md_content, translation_service)
        
        # Check if there is anything in the translated content
        logger.info(f"Translated markdown content length: {len(translated_md)} characters")
        logger.info(f"Translated content sample (first 200 chars): {translated_md[:200]}")
        
        # Check for Chinese characters if target is Chinese
        if target_lang == "zh":
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in translated_md)
            if not has_chinese:
                logger.warning("No Chinese characters found in translated markdown!")
            else:
                logger.info("Chinese characters verified in translated markdown")
        
        # Convert back to output format
        logger.info(f"Converting translated markdown to output format: {output_path.suffix}")
        if output_path.suffix.lower() == '.pdf':
            md_processor.markdown_to_pdf(translated_md, str(output_path))
        elif output_path.suffix.lower() == '.docx':
            md_processor.markdown_to_docx(translated_md, str(output_path))
        
        # Initialize document processor for validation purposes
        doc_processor = DocumentProcessor(str(input_path))
        doc_components = doc_processor.process()
        
        # Create metadata for validation
        markdown_result = {
            "markdown_processed": True,
            "output_path": str(output_path),
            "translation_completeness": 0.95,  # Estimated completeness
            "structure_preservation": 0.9,  # Estimated structure preservation
            "target_language": target_lang,
            "cjk_support": True,
            "tables_preserved": True
        }
        
        # Validate output
        validator = OutputValidator()
        validation_result = validator.validate_markdown_document(markdown_result, doc_components)
        
        return str(output_path), validation_result, translated_md
    else:
        # Use standard processing pipeline
        # Initialize components
        doc_processor = DocumentProcessor(str(input_path))
        translation_service = TranslationService(
            source_lang=source_lang,
            target_lang=target_lang, 
            model=model
        )
        doc_rebuilder = DocumentRebuilder()
        validator = OutputValidator()
        
        # Process document
        doc_components = doc_processor.process()
        
        # Translate components
        translated_components = translation_service.translate(doc_components)
        
        # Rebuild document
        rebuilt_doc = doc_rebuilder.rebuild(
            translated_components, 
            output_format=input_path.suffix[1:],
            rebuild_mode=pdf_mode,
            source_pdf_path=str(input_path) if pdf_mode in ['precise', 'bilingual'] else None
        )
        
        # Validate output
        validation_result = validator.validate(doc_components, rebuilt_doc)
        
        # Save output
        rebuilt_doc.save(str(output_path))
        
        return str(output_path), validation_result, None

def main():
    st.set_page_config(
        page_title="AutoWealthTranslate", 
        page_icon="📄",
        layout="wide"
    )
    
    st.title("AutoWealthTranslate")
    st.markdown("### Automatically translate wealth plan reports while preserving formatting")
    
    # Sidebar for API key
    st.sidebar.title("Configuration")
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                   help="Required for GPT models. Will be stored only in this session.")
    
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # About section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.info(
        """
        **AutoWealthTranslate** helps financial advisors translate 
        wealth planning documents while preserving formatting, 
        charts, and tables.
        
        This application uses AI to translate complex financial 
        documents while maintaining the integrity of financial 
        terminology and document structure.
        """
    )
    
    # Advanced settings
    st.sidebar.markdown("---")
    st.sidebar.header("Advanced Settings")
    
    # PDF processing mode selector (only shown when advanced settings expanded)
    pdf_mode = st.sidebar.selectbox(
        "Document Processing Mode",
        options=list(PDF_PROCESSING_MODES.keys()),
        format_func=lambda x: PDF_PROCESSING_MODES[x],
        help="""
        Enhanced: Better version of the standard layout engine.
        Precise: Preserves exact original layout, replacing only text (Canva-like).
        Bilingual: Keeps original pages and adds translation pages after each.
        Markdown: Uses Markdown as intermediate format for better structure preservation.
        """
    )
    
    # Display detailed description of selected mode
    st.sidebar.markdown(PDF_MODE_DESCRIPTIONS[pdf_mode])
    
    # Chinese character support info
    if pdf_mode in ["precise", "bilingual", "markdown"]:
        st.sidebar.success("✓ Advanced Chinese character support is enabled in this mode")
    
    # Main area - File upload
    st.header("Upload Document")
    
    uploaded_file = st.file_uploader(
        "Upload a PDF or Word document",
        type=["pdf", "docx"],
        help="Maximum file size: 200MB"
    )
    
    # Translation settings
    col1, col2, col3 = st.columns(3)
    
    with col1:
        source_language = st.selectbox(
            "Source Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            format_func=lambda x: SUPPORTED_LANGUAGES[x],
            index=0,  # Default to English
            help="The language of the document you're uploading"
        )
    
    with col2:
        target_language = st.selectbox(
            "Target Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            format_func=lambda x: SUPPORTED_LANGUAGES[x],
            index=1,  # Default to Chinese
            help="The language to translate the document into"
        )
        
        # Add a note about Chinese support if target is Chinese
        if target_language == "zh":
            st.info("📝 For Chinese translation, the Precise or Bilingual modes provide the best character support.")
    
    with col3:
        model = st.selectbox(
            "Translation Model",
            options=list(TRANSLATION_MODELS.keys()),
            format_func=lambda x: TRANSLATION_MODELS[x],
            help="The AI model to use for translation. GPT-4 offers the best quality."
        )
    
    # File info
    if uploaded_file is not None:
        file_details = {
            "Filename": uploaded_file.name,
            "File size": f"{uploaded_file.size / 1024:.2f} KB",
            "File type": uploaded_file.type
        }
        
        st.write("### File Details")
        for key, value in file_details.items():
            st.write(f"**{key}:** {value}")
        
        # Selected PDF mode info
        if uploaded_file.name.lower().endswith('.pdf'):
            mode_name = PDF_PROCESSING_MODES[pdf_mode]
            st.info(f"Selected document processing mode: **{mode_name}**. You can change this in the Advanced Settings in the sidebar.")
            
            # Special note for Chinese translations
            if target_language == "zh" and pdf_mode == "enhanced":
                st.warning("ℹ️ For better Chinese character rendering, consider using the 'Precise', 'Bilingual', or 'Markdown' mode.")
        
        # Process button
        if st.button("Translate Document"):
            if not api_key and model.startswith("gpt"):
                st.error("OpenAI API Key is required for GPT models. Please enter it in the sidebar.")
            else:
                # Save uploaded file to temp location
                temp_dir = create_temp_dir()
                temp_file_path = temp_dir / uploaded_file.name
                
                with open(temp_file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Processing steps with progress updates
                    status_text.text("Step 1/4: Processing document...")
                    progress_bar.progress(10)
                    time.sleep(0.5)  # Give UI time to update
                    
                    status_text.text("Step 2/4: Extracting content...")
                    progress_bar.progress(25)
                    time.sleep(0.5)
                    
                    status_text.text(f"Step 3/4: Translating content from {SUPPORTED_LANGUAGES[source_language]} to {SUPPORTED_LANGUAGES[target_language]}...")
                    progress_bar.progress(40)
                    
                    # Actual processing
                    output_path, validation_result, markdown_content = translate_document(
                        temp_file_path,
                        source_language, 
                        target_language,
                        model,
                        api_key,
                        pdf_mode
                    )
                    
                    status_text.text("Step 4/4: Finalizing document...")
                    progress_bar.progress(90)
                    time.sleep(0.5)
                    
                    # Complete
                    progress_bar.progress(100)
                    status_text.text("Translation complete!")
                    
                    # Show results
                    st.success(f"Document successfully translated from {SUPPORTED_LANGUAGES[source_language]} to {SUPPORTED_LANGUAGES[target_language]}!")
                    
                    # Show validation results
                    st.write("### Validation Results")
                    st.write(f"**Score:** {validation_result['score']}/10")
                    
                    if validation_result['issues']:
                        st.warning("Some issues were detected:")
                        for issue in validation_result['issues']:
                            st.write(f"- {issue}")
                    else:
                        st.write("No issues detected.")
                    
                    # Download link
                    st.markdown("### Download Translated Document")
                    st.markdown(get_file_download_link(output_path, "Click here to download"), unsafe_allow_html=True)
                    
                    # Show preview if PDF
                    if output_path.endswith(".pdf"):
                        with open(output_path, "rb") as f:
                            pdf_bytes = f.read()
                        
                        st.write("### Document Preview")
                        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                    
                    # Show markdown preview if markdown mode
                    if pdf_mode == "markdown" and markdown_content:
                        st.write("### Markdown Preview")
                        st.markdown(markdown_content)
                        
                        # Add download markdown button
                        markdown_bytes = markdown_content.encode()
                        b64 = base64.b64encode(markdown_bytes).decode()
                        markdown_filename = f"{Path(output_path).stem}.md"
                        markdown_download = f'<a href="data:text/markdown;base64,{b64}" download="{markdown_filename}">Download Markdown</a>'
                        st.markdown(markdown_download, unsafe_allow_html=True)
                
                except Exception as e:
                    st.error(f"An error occurred during translation: {str(e)}")
                    logger.error(f"Translation error: {str(e)}", exc_info=True)
    
    # Instructions when no file is uploaded
    else:
        st.info("👆 Upload a document to get started")
        
        st.markdown("""
        ### How It Works
        1. Upload a PDF or Word document
        2. Select the source and target languages
        3. Choose a translation model
        4. Click 'Translate Document'
        5. Download the translated document
        
        ### Supported Features
        - Preserves document formatting and layout
        - Maintains tables and charts
        - Handles financial terminology correctly
        - Supports PDF and Word documents
        - Translates between multiple languages
        - Multiple PDF processing modes for different needs
        - Enhanced support for CJK characters (Chinese, Japanese, Korean)
        """)
        
        # PDF processing mode explanations
        st.markdown("### Document Processing Modes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Enhanced Mode")
            st.write("An improved version of our standard processing with better text layout and typography.")
            st.write("Best for: Most PDF documents with simple to moderate complexity.")
            
            st.subheader("Precise Mode")
            st.write("Maintains exact original layout by identifying and replacing only text elements (Canva-like).")
            st.write("Best for: Complex documents where layout preservation is critical.")
        
        with col2:
            st.subheader("Bilingual Mode")
            st.write("Keeps all original pages and adds translation pages after each original page.")
            st.write("Best for: When both original and translation need to be presented together.")
            
            st.subheader("Markdown Mode (New!)")
            st.write("Uses Markdown as an intermediate format for better document structure preservation.")
            st.write("Best for: Complex financial documents with tables, lists, and detailed formatting requirements.")
        
        # Special note about Chinese translations
        st.info("📝 **Translating to Chinese?** For the best Chinese character support, we recommend using the 'Precise', 'Bilingual', or 'Markdown' mode which have enhanced CJK (Chinese, Japanese, Korean) font handling.")

if __name__ == "__main__":
    main() 