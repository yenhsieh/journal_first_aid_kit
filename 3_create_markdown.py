#!/usr/bin/env python3
"""
Create Standardized Markdown Files

This script takes text files containing paper data and Claude's analysis,
and formats them into standardized markdown files with YAML frontmatter.

Usage:
    python 3_create_markdown.py /path/to/text_folder /path/to/markdown_folder
"""

import os
import re
import sys
import glob
import yaml
import logging
import argparse
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extract_data_from_file(txt_path):
    """Extract all data from a text file including Claude's analysis"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata
        title_match = re.search(r'TITLE: (.*?)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Unknown Title"
        
        authors_match = re.search(r'AUTHORS: (.*?)$', content, re.MULTILINE)
        authors = authors_match.group(1) if authors_match else "Unknown Authors"
        
        year_match = re.search(r'YEAR: (.*?)$', content, re.MULTILINE)
        year = year_match.group(1) if year_match else "Unknown Year"
        
        # Extract abstract
        abstract_match = re.search(r'ABSTRACT:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                                 content, re.DOTALL)
        abstract = abstract_match.group(1).strip() if abstract_match else ""
        
        # Extract introduction
        intro_match = re.search(r'INTRODUCTION:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                              content, re.DOTALL)
        introduction = intro_match.group(1).strip() if intro_match else ""
        
        # Extract Claude analysis sections
        claude_match = re.search(r'CLAUDE ANALYSIS:\s*(.*?)$', content, re.DOTALL)
        claude_analysis = claude_match.group(1).strip() if claude_match else ""
        
        # Parse Claude analysis
        summary = ""
        gap = ""
        objectives = ""
        keywords = []
        
        if claude_analysis:
            summary_match = re.search(r'SUMMARY:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                                    claude_analysis, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ""
            
            gap_match = re.search(r'RESEARCH GAP/PROBLEM:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                                claude_analysis, re.DOTALL)
            gap = gap_match.group(1).strip() if gap_match else ""
            
            obj_match = re.search(r'OBJECTIVES:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                                claude_analysis, re.DOTALL)
            objectives = obj_match.group(1).strip() if obj_match else ""
            
            kw_match = re.search(r'KEYWORDS:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                               claude_analysis, re.DOTALL)
            if kw_match:
                keywords_text = kw_match.group(1).strip()
                keywords = [k.strip() for k in keywords_text.split(',')]
        
        return {
            "title": title,
            "authors": authors,
            "year": year,
            "abstract": abstract,
            "introduction": introduction,
            "summary": summary,
            "gap": gap,
            "objectives": objectives,
            "keywords": keywords
        }
    except Exception as e:
        logging.error(f"Error extracting data from {txt_path}: {e}")
        return None

def clean_author_for_yaml(author_text):
    """Clean up author text for YAML frontmatter"""
    # Remove problematic characters
    cleaned = re.sub(r'[^\w\s,;.-]', '', author_text)
    # Remove extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def ensure_keywords_in_singular(keywords):
    """Ensure keywords are in singular form"""
    singular_keywords = []
    
    for keyword in keywords:
        # Common plural endings to convert to singular
        if keyword.endswith('ies') and not keyword.endswith('series'):
            singular = keyword[:-3] + 'y'
        elif keyword.endswith('es') and not keyword.endswith(('species', 'series')):
            singular = keyword[:-2]
        elif keyword.endswith('s') and not keyword.endswith(('ss', 'is', 'us', 'os')):
            singular = keyword[:-1]
        else:
            singular = keyword
        
        # Add to list, excluding empty strings
        if singular:
            singular_keywords.append(singular)
    
    return singular_keywords

def create_markdown_file(data, output_path):
    """Create a markdown file with standardized format using H1 headings"""
    try:
        # Ensure keywords are in singular form
        keywords = ensure_keywords_in_singular(data["keywords"])
        
        # Before adding the formatted sections, check and clean the summary
        if data["summary"] and "RESEARCH GAP/PROBLEM:" in data["summary"]:
            # Remove the raw section from summary
            data["summary"] = re.sub(r'RESEARCH GAP/PROBLEM:.*?(?=\n\n[A-Z]+:|\Z)', '', data["summary"], flags=re.DOTALL)
            data["summary"] = data["summary"].strip()
        
        # Create YAML frontmatter
        frontmatter = {
            'title': data["title"],
            'author': clean_author_for_yaml(data["authors"]),
            'year': data["year"],
            'tags': keywords
        }
        
        # Convert to YAML
        yaml_content = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        
        # Build markdown content with H1 headings for each section
        md_content = f"---\n{yaml_content}---\n\n"
        
        # Add all sections with consistent H1 headings
        md_content += f"# TITLE\n{data['title']}\n\n"
        md_content += f"# AUTHOR\n{data['authors']}\n\n"
        
        # Add SUMMARY section
        if data["summary"]:
            md_content += f"# SUMMARY\n{data['summary']}\n\n"
        
        # Add KEYWORDS section immediately after SUMMARY
        if keywords:
            md_content += f"# KEYWORDS\n{', '.join(['#' + k for k in keywords])}\n\n"
        
        # Add RESEARCH GAP/PROBLEM section
        if data["gap"]:
            md_content += f"# RESEARCH GAP/PROBLEM\n{data['gap']}\n\n"
        
        # Add OBJECTIVES section
        if data["objectives"]:
            md_content += f"# OBJECTIVES\n{data['objectives']}\n\n"
        
        # Add ABSTRACT section if available
        if data["abstract"]:
            md_content += f"# ABSTRACT\n{data['abstract']}\n\n"
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logging.info(f"Created markdown file: {output_path}")
        return True
    except Exception as e:
        logging.error(f"Error creating markdown file: {e}")
        return False

def get_base_name(txt_path):
    """Get base name for markdown file from text file path"""
    base_name = os.path.basename(txt_path)
    base_name = os.path.splitext(base_name)[0]
    return base_name

def process_text_folder(text_folder, markdown_folder, overwrite=False):
    """Process all text files in a folder and create markdown files"""
    # Create output directory if it doesn't exist
    os.makedirs(markdown_folder, exist_ok=True)
    
    # Get all text files
    txt_files = glob.glob(os.path.join(text_folder, "*.txt"))
    logging.info(f"Found {len(txt_files)} text files to process")
    
    success_count = 0
    skipped_count = 0
    for i, txt_path in enumerate(txt_files):
        txt_filename = os.path.basename(txt_path)
        logging.info(f"Processing file {i+1}/{len(txt_files)}: {txt_filename}")
        
        # Check if markdown file already exists
        base_name = get_base_name(txt_path)
        md_path = os.path.join(markdown_folder, f"{base_name}.md")
        
        if os.path.exists(md_path) and not overwrite:
            logging.info(f"Skipping {txt_filename} - Markdown file already exists")
            skipped_count += 1
            continue
        
        if process_single_text_file(txt_path, markdown_folder, overwrite):
            success_count += 1
    
    logging.info(f"Completed processing {len(txt_files)} files:")
    logging.info(f"  - {success_count} successfully processed")
    logging.info(f"  - {skipped_count} skipped (files already exist)")
    logging.info(f"  - {len(txt_files) - success_count - skipped_count} failed")
    
    return success_count

def process_single_text_file(txt_path, markdown_folder, overwrite=False):
    """Process a single text file and create a markdown file"""
    if not os.path.exists(txt_path):
        logging.error(f"Text file does not exist: {txt_path}")
        return False
        
    if not txt_path.lower().endswith('.txt'):
        logging.error(f"File is not a text file: {txt_path}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(markdown_folder, exist_ok=True)
    
    # Get base name for markdown file
    base_name = get_base_name(txt_path)
    md_path = os.path.join(markdown_folder, f"{base_name}.md")
    
    # Check if markdown file already exists
    if os.path.exists(md_path) and not overwrite:
        logging.info(f"Skipping {os.path.basename(txt_path)} - Markdown file already exists (use --overwrite to replace)")
        return True
    
    logging.info(f"Processing text file: {os.path.basename(txt_path)}")
    
    # Extract data from file
    data = extract_data_from_file(txt_path)
    if not data:
        logging.error(f"Failed to extract data from {txt_path}")
        return False
    
    # Check if there's a Claude analysis
    if not data["summary"] and not data["keywords"]:
        logging.warning(f"No Claude analysis found in {txt_path}")
        return False
    
    # Create markdown file
    if create_markdown_file(data, md_path):
        logging.info(f"Successfully created markdown file: {os.path.basename(md_path)}")
        return True
    else:
        logging.error(f"Failed to create markdown file for {txt_path}")
        return False
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create markdown files from processed text files")
    parser.add_argument("input_path", help="Path to text file or folder containing text files")
    parser.add_argument("markdown_folder", help="Output folder for markdown files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing markdown files")
    
    args = parser.parse_args()
    
    # Check if input is a file or directory
    if os.path.isfile(args.input_path):
        # Process single file
        if process_single_text_file(args.input_path, args.markdown_folder, args.overwrite):
            print(f"Successfully processed {os.path.basename(args.input_path)}")
            sys.exit(0)
        else:
            print(f"Failed to process {os.path.basename(args.input_path)}")
            sys.exit(1)
    elif os.path.isdir(args.input_path):
        # Process directory - update this function to pass overwrite param
        process_text_folder(args.input_path, args.markdown_folder, args.overwrite)
        sys.exit(0)
    else:
        print(f"Error: {args.input_path} is neither a valid file nor directory")
        sys.exit(1)