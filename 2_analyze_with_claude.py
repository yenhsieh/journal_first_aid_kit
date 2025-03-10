#!/usr/bin/env python3
"""
Analyze Paper Content with Claude API

This script takes text files containing paper data (title, abstract, introduction),
sends them to Claude API for analysis, and appends the results to the same files.

Usage:
    python 2_analyze_with_claude.py /path/to/text_folder [--overwrite]
    
Options:
    --overwrite     Overwrite existing Claude analysis if already present in the file
"""

import os
import re
import sys
import glob
import time
import logging
import argparse
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Get Claude API key from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20240620")  # Default model

def initialize_claude():
    """Initialize the Claude API client"""
    if not ANTHROPIC_API_KEY:
        logging.error("ANTHROPIC_API_KEY not found in environment variables")
        return None
    
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        logging.info(f"Claude API client initialized (model: {CLAUDE_MODEL})")
        return client
    except Exception as e:
        logging.error(f"Error initializing Claude API client: {e}")
        return None

def has_claude_analysis(txt_path):
    """Check if the text file already has Claude analysis"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Claude analysis section
        return "CLAUDE ANALYSIS:" in content
    except Exception as e:
        logging.error(f"Error checking for Claude analysis in {txt_path}: {e}")
        return False

def extract_content_from_file(txt_path):
    """Extract title, abstract, and introduction from a text file"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title
        title_match = re.search(r'TITLE: (.*?)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Unknown Title"
        
        # Extract abstract
        abstract_match = re.search(r'ABSTRACT:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                                 content, re.DOTALL)
        abstract = abstract_match.group(1).strip() if abstract_match else ""
        
        # Extract introduction
        intro_match = re.search(r'INTRODUCTION:\s*(.*?)(?=\n\n[A-Z]+:|\Z)', 
                              content, re.DOTALL)
        introduction = intro_match.group(1).strip() if intro_match else ""
        
        return {
            "title": title,
            "abstract": abstract,
            "introduction": introduction,
            "content": content
        }
    except Exception as e:
        logging.error(f"Error extracting content from {txt_path}: {e}")
        return None

def analyze_with_claude(client, title, abstract, introduction):
    """
    Use Claude API to analyze paper content
    
    Returns a string with analysis results
    """
    if not client:
        return "ERROR: Claude API client not initialized"
    
    # Combine abstract and introduction, prioritizing whichever is available
    analysis_text = ""
    if abstract:
        analysis_text += f"Abstract:\n{abstract}\n\n"
    if introduction:
        analysis_text += f"Introduction:\n{introduction}\n\n"
    
    if not analysis_text:
        return "ERROR: No content available for analysis"
    
    # Prepare prompt for Claude
    prompt = f"""
    I have content from a scientific paper that I need you to analyze. Please:

    1. Summarize the key points in 4-6 sentences
    2. Identify the main research gap or problem being addressed
    3. Extract the paper's apparent objectives or research questions
    4. Generate EXACTLY 5 important keywords/concepts. Choose only the most critical 5 terms that best represent the paper.

    When generating keywords, please follow these rules:
    - Use SINGULAR forms only (e.g., "biomarker" not "biomarkers")
    - Use underscores instead of spaces (e.g., "gene_expression")
    - Maintain standard capitalization for abbreviations (RNA-Seq, miRNA, DNA)

    Title: {title}

    {analysis_text}

    Respond in this format:
    SUMMARY:
    [Your summary here]

    RESEARCH GAP/PROBLEM:
    [Identified research gap or problem]

    OBJECTIVES:
    [Research objectives/questions]

    KEYWORDS:
    [5 singular keywords separated by commas]
    """
    
    try:
        logging.info(f"Sending request to Claude API (model: {CLAUDE_MODEL})")
        start_time = time.time()
        
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system="You are an expert at analyzing scientific literature. Focus on extracting the most important information accurately.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        elapsed_time = time.time() - start_time
        logging.info(f"Received response from Claude API (time: {elapsed_time:.2f}s)")
        
        return response.content[0].text
    except Exception as e:
        logging.error(f"Error calling Claude API: {e}")
        return f"ERROR: Claude API request failed - {str(e)}"

def append_analysis_to_file(txt_path, analysis_result):
    """Append Claude's analysis to the text file"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if analysis is already appended
        if "CLAUDE ANALYSIS:" in content:
            # Remove existing analysis
            content = re.sub(r'\n\nCLAUDE ANALYSIS:.*$', '', content, flags=re.DOTALL)
        
        # Append analysis
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.write("\n\nCLAUDE ANALYSIS:\n")
            f.write(analysis_result)
        
        logging.info(f"Analysis appended to {txt_path}")
        return True
    except Exception as e:
        logging.error(f"Error appending analysis to {txt_path}: {e}")
        return False

def process_text_files(text_folder, overwrite=False):
    """Process all text files in the folder with Claude API"""
    # Initialize Claude client
    client = initialize_claude()
    if not client:
        logging.error("Failed to initialize Claude client, exiting")
        return
    
    # Get all text files
    txt_files = glob.glob(os.path.join(text_folder, "*.txt"))
    logging.info(f"Found {len(txt_files)} text files to process")
    
    success_count = 0
    skipped_count = 0
    
    for i, txt_path in enumerate(txt_files):
        txt_filename = os.path.basename(txt_path)
        logging.info(f"Processing file {i+1}/{len(txt_files)}: {txt_filename}")
        
        # Check if file already has Claude analysis
        if has_claude_analysis(txt_path) and not overwrite:
            logging.info(f"Skipping {txt_filename} - Claude analysis already exists (use --overwrite to replace)")
            skipped_count += 1
            continue
        
        # Extract content from file
        content = extract_content_from_file(txt_path)
        if not content:
            logging.error(f"Failed to extract content from {txt_filename}, skipping")
            continue
        
        # Check if there's content to analyze
        if not content["abstract"] and not content["introduction"]:
            logging.warning(f"No abstract or introduction found in {txt_filename}, skipping")
            continue
        
        # Analyze with Claude
        analysis_result = analyze_with_claude(
            client,
            content["title"],
            content["abstract"],
            content["introduction"]
        )
        
        if analysis_result.startswith("ERROR:"):
            logging.error(f"Analysis failed for {txt_filename}: {analysis_result}")
            continue
        
        # Append analysis to file
        if append_analysis_to_file(txt_path, analysis_result):
            success_count += 1
        
        # Add a small delay to avoid rate limiting
        if i < len(txt_files) - 1:
            time.sleep(1)
    
    logging.info(f"Completed processing {len(txt_files)} files:")
    logging.info(f"  - {success_count} successfully analyzed")
    logging.info(f"  - {skipped_count} skipped (analysis already exists)")
    logging.info(f"  - {len(txt_files) - success_count - skipped_count} failed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze text files with Claude API")
    parser.add_argument("text_folder", help="Folder containing text files to analyze")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Claude analysis if present")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.text_folder):
        print(f"Error: {args.text_folder} is not a valid directory")
        sys.exit(1)
    
    logging.info(f"Processing text files in: {args.text_folder}")
    if args.overwrite:
        logging.info("Overwrite mode enabled - existing analyses will be replaced")
    
    process_text_files(args.text_folder, args.overwrite)