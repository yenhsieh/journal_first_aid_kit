#!/usr/bin/env python3
"""
Extract Paper Data

This script extracts introduction text and metadata from PDF files,
and fetches abstracts from Zotero when available.

Usage:
    python 1_extract_paper_data.py /path/to/pdf_folder /path/to/output_folder
"""

import os
import re
import sys
import glob
import fitz  # PyMuPDF
import logging
from dotenv import load_dotenv
from pyzotero import zotero

# Import the existing introduction extractor
import extract_introduction

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Zotero API credentials
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY_TYPE = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

def initialize_zotero():
    """Initialize Zotero client if credentials are available"""
    if not ZOTERO_LIBRARY_ID or not ZOTERO_API_KEY:
        logging.warning("Zotero API credentials not found. Abstract retrieval will be skipped.")
        return None
    
    try:
        zot = zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)
        # Test connection
        zot.items(limit=1)
        logging.info("Successfully connected to Zotero API")
        return zot
    except Exception as e:
        logging.error(f"Error initializing Zotero: {e}")
        return None

def extract_title_authors_from_pdf(pdf_path):
    """Extract title and authors from PDF metadata or first page"""
    try:
        doc = fitz.open(pdf_path)
        
        # Try metadata first
        metadata = doc.metadata
        title = metadata.get("title", "").strip()
        authors = metadata.get("author", "").strip()
        
        # If not found in metadata, try first page
        if not title or title.lower() in ["untitled", "document", ""]:
            first_page_text = doc[0].get_text()
            lines = first_page_text.split('\n')
            
            # Assume first non-empty line is title
            for line in lines:
                if line.strip():
                    title = line.strip()
                    break
        
        if not authors or authors in ["Unknown Author", ""]:
            # Look for author line in first few lines
            first_page_text = doc[0].get_text()
            lines = first_page_text.split('\n')
            
            for i, line in enumerate(lines[:15]):
                if re.search(r'by|authors?:|et al\.|\bcorresponding author\b', line, re.IGNORECASE):
                    authors = line.strip()
                    # Clean up author line
                    authors = re.sub(r'^\s*(by|authors?:|corresponding author:?)\s*', '', authors, flags=re.IGNORECASE)
                    break
        
        return title, authors
    except Exception as e:
        logging.error(f"Error extracting metadata from PDF: {e}")
        return "Unknown Title", "Unknown Author"

def extract_year(pdf_path):
    """Extract year from filename or PDF content"""
    # Try filename first
    filename = os.path.basename(pdf_path)
    year_match = re.search(r'(\d{4})', filename)
    if year_match:
        return year_match.group(1)
    
    # Try PDF metadata
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        
        # Look in metadata date fields
        for field in ["creationDate", "modDate"]:
            if field in metadata and metadata[field]:
                date_match = re.search(r'D:(\d{4})', metadata[field])
                if date_match:
                    return date_match.group(1)
        
        # Look in first page text
        first_page_text = doc[0].get_text()
        year_match = re.search(r'\b(19|20)\d{2}\b', first_page_text[:1000])
        if year_match:
            return year_match.group(0)
    except Exception as e:
        logging.error(f"Error extracting year from PDF: {e}")
    
    return "Unknown Year"

def normalize_filename(pdf_path):
    """
    Convert PDF filename to the desired format: 'Revkov_et_al_2023'
    """
    # Get just the filename without path and extension
    base_name = os.path.basename(pdf_path)
    base_name = os.path.splitext(base_name)[0]
    
    # Try different common patterns
    
    # Pattern 1: 'Author et al. - Year - Title'
    match = re.match(r'(.*?)\s*-\s*(\d{4})\s*-\s*(.*)', base_name)
    if match:
        author, year, _ = match.groups()
        # Clean up author part (replace dots, capitalize properly)
        author = author.strip().replace('.', '')
        # Replace spaces with underscores
        author = author.replace(' ', '_')
        # Remove any other special characters
        author = re.sub(r'[^\w_]', '', author)
        return f"{author}_{year}"
    
    # Pattern 2: 'Author et al_Year_Title'
    match = re.match(r'(.*?)_(\d{4})_(.*)', base_name)
    if match:
        author, year, _ = match.groups()
        # Replace spaces with underscores
        author = author.replace(' ', '_')
        # Remove any other special characters
        author = re.sub(r'[^\w_]', '', author)
        return f"{author}_{year}"
    
    # Pattern 3: Look for a year (4 digits) and an author name before it
    match = re.search(r'(.*?)(?:\s|_)(\d{4})(?:\s|_)', base_name)
    if match:
        author, year = match.groups()
        # Clean up author part
        author = author.replace('.', '').strip()
        # Replace spaces with underscores
        author = author.replace(' ', '_')
        # Remove any other special characters
        author = re.sub(r'[^\w_]', '', author)
        return f"{author}_{year}"
    
    # Fallback: just clean up the filename
    clean_name = re.sub(r'[^\w]', '_', base_name)
    # Avoid double underscores
    clean_name = re.sub(r'_+', '_', clean_name)
    return clean_name

def find_in_zotero(zot, title, authors, year=None):
    """Find a paper in Zotero using title, authors, and year"""
    if not zot or not title:
        return None
    
    try:
        # Clean title for search
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        title_words = clean_title.split()
        
        # Take first few words for search to avoid overly complex queries
        search_terms = ' '.join(title_words[:5]) if len(title_words) > 5 else clean_title
        
        logging.info(f"Searching Zotero for: {search_terms}")
        results = zot.items(q=search_terms, limit=5)
        
        if not results:
            logging.info("No results found in Zotero")
            return None
        
        # Find best match
        for item in results:
            item_title = item.get('data', {}).get('title', '')
            # Simple string matching - if substantial overlap
            if (clean_title.lower() in item_title.lower() or 
                item_title.lower() in clean_title.lower()):
                
                # If year provided, check if it matches
                if year and year != "Unknown Year":
                    if year not in item.get('data', {}).get('date', ''):
                        continue
                
                logging.info(f"Found match in Zotero: {item_title}")
                return item
        
        # If no clear match, return first result
        logging.info(f"No exact match, using closest result: {results[0].get('data', {}).get('title', '')}")
        return results[0]
        
    except Exception as e:
        logging.error(f"Error searching Zotero: {e}")
        return None

def process_pdf_with_zotero(pdf_path, output_folder, zot=None):
    """
    Process a PDF file to extract introduction and metadata,
    and fetch abstract from Zotero
    """
    pdf_filename = os.path.basename(pdf_path)
    logging.info(f"Processing: {pdf_filename}")
    
    # Extract introduction
    introduction_text, intro_metadata = extract_introduction.process_file(pdf_path)
    
    if not introduction_text:
        logging.error(f"Failed to extract introduction from {pdf_filename}")
        introduction_text = "Introduction extraction failed."
    
    # Extract basic metadata from PDF
    title, authors = extract_title_authors_from_pdf(pdf_path)
    logging.info(f"Title: {title}")
    logging.info(f"Authors: {authors}")
    
    # Extract year
    year = extract_year(pdf_path)
    logging.info(f"Year: {year}")
    
    # Normalize filename for output
    base_name = normalize_filename(pdf_path)
    logging.info(f"Base name for output: {base_name}")
    
    # Try to find in Zotero and get abstract
    abstract = ""
    zotero_item = None
    
    if zot:
        zotero_item = find_in_zotero(zot, title, authors, year)
        if zotero_item:
            abstract = zotero_item.get('data', {}).get('abstractNote', '')
            if abstract:
                logging.info(f"Found abstract in Zotero ({len(abstract)} characters)")
            else:
                logging.info("No abstract found in Zotero")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Save all to text file
    output_path = os.path.join(output_folder, f"{base_name}.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"TITLE: {title}\n")
        f.write(f"AUTHORS: {authors}\n")
        f.write(f"YEAR: {year}\n")
        f.write(f"\nABSTRACT:\n{abstract}\n")
        f.write(f"\nINTRODUCTION:\n{introduction_text}\n")
    
    logging.info(f"Saved extracted data to: {output_path}")
    
    return {
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": abstract,
        "introduction": introduction_text,
        "output_path": output_path,
        "base_name": base_name
    }

def process_pdf_folder(pdf_folder, output_folder):
    """Process all PDFs in a folder"""
    # Initialize Zotero client
    zot = initialize_zotero()
    
    # Get all PDF files in the folder
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    logging.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF
    results = []
    for i, pdf_path in enumerate(pdf_files):
        logging.info(f"Processing file {i+1}/{len(pdf_files)}")
        result = process_pdf_with_zotero(pdf_path, output_folder, zot)
        results.append(result)
    
    logging.info(f"Completed processing {len(pdf_files)} PDF files")
    return results

# Add this function to 1_extract_paper_data.py
def process_single_pdf(pdf_path, output_folder):
    """Process a single PDF file"""
    if not os.path.exists(pdf_path):
        logging.error(f"PDF file does not exist: {pdf_path}")
        return False
        
    if not pdf_path.lower().endswith('.pdf'):
        logging.error(f"File is not a PDF: {pdf_path}")
        return False
    
    # Initialize Zotero client
    zot = initialize_zotero()
    
    # Process the PDF
    logging.info(f"Processing single PDF: {os.path.basename(pdf_path)}")
    result = process_pdf_with_zotero(pdf_path, output_folder, zot)
    
    if result:
        logging.info(f"Successfully processed {os.path.basename(pdf_path)}")
        return True
    else:
        logging.error(f"Failed to process {os.path.basename(pdf_path)}")
        return False
        
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python 1_extract_paper_data.py /path/to/pdf_file_or_folder /path/to/output_folder")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_folder = sys.argv[2]
    
    # Check if input is a file or directory
    if os.path.isfile(input_path):
        # Process single file
        if process_single_pdf(input_path, output_folder):
            print(f"Successfully processed {os.path.basename(input_path)}")
            sys.exit(0)
        else:
            print(f"Failed to process {os.path.basename(input_path)}")
            sys.exit(1)
    elif os.path.isdir(input_path):
        # Process directory
        process_pdf_folder(input_path, output_folder)
        sys.exit(0)
    else:
        print(f"Error: {input_path} is neither a valid file nor directory")
        sys.exit(1)