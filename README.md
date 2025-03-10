# Scientific Paper Processing Pipeline

This repository contains three Python scripts that work together to process scientific papers, extract key information, analyze content with Claude AI, and create standardized markdown files for knowledge management.
Key information specifically focusing on **Abstract** and **Introduction** sections, which I personally believe the crucial part suggesting the direction and scope of the research article.

[03.10.2025] Module _1_extract_paper_data.py_ currently is not 100% capturing the introduction part, use with caution.

## AI tools disclosure

The work is done by coworking with Claude 3.7 Sonnet.

## Overview

The pipeline consists of three main steps:

1. **Extract paper data**: Extract introduction text from PDFs, fetch abstracts from Zotero, and save to structured text files
2. **Analyze with Claude**: Use Claude API to analyze the content and generate summaries, research gaps, objectives, and keywords
3. **Create markdown files**: Format the analyzed content into standardized markdown files with YAML frontmatter

## API Usage

**Important note about API access:**

- **Zotero API**: Free to use with standard rate limits (up to 300 requests per minute). You only need to create a Zotero account and generate an API key.

- **Claude API**: Requires a paid subscription to Anthropic. You will need to sign up for an account at [anthropic.com](https://www.anthropic.com/) and purchase API credits. The script uses Claude to analyze paper content, so this part of the pipeline will incur costs based on your usage.

If you don't have access to the Claude API, you can still use the first script to extract data from PDFs and get abstracts from Zotero, then perform the analysis manually or with another tool.

## Requirements

### Python Packages

```
pip install pyzotero PyMuPDF anthropic python-dotenv pyyaml
```

- **pyzotero**: Interface with Zotero API
- **PyMuPDF** (aka fitz): Process PDF files
- **anthropic**: Access the Claude API
- **python-dotenv**: Load environment variables
- **pyyaml**: Handle YAML frontmatter

### External Dependencies

- **extract_introduction.py**: Script to extract introductions from PDFs (imported by the first script)

### Environment Variables

Create a `.env` file in the PDF directory with the following variables:

```
# Zotero API credentials (free)
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_API_KEY=your_api_key
ZOTERO_LIBRARY_TYPE=user

# Claude API credentials (paid subscription required)
ANTHROPIC_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20240620
```

## Getting API Keys

### Zotero API Key
1. Create a Zotero account at [zotero.org](https://www.zotero.org/) if you don't have one
2. Go to [Settings → Feeds/API](https://www.zotero.org/settings/keys)
3. Click "Create new private key"
4. Set appropriate permissions (read-only is sufficient for this pipeline)
5. Your library ID is visible in the URL when viewing your library: `https://www.zotero.org/users/XXXXXXX/`

### Claude API Key
1. Sign up for an Anthropic account at [anthropic.com](https://www.anthropic.com/)
2. Subscribe to a paid plan for API access
3. Generate an API key from your dashboard
4. Note that usage will be billed based on the number of tokens processed

## Scripts

### 1. Extract Paper Data (`1_extract_paper_data.py`)

Extracts introduction text from PDFs and fetches abstracts from Zotero when available.
PDF files are previously renamed via [ZotFile](https://zotfile.com/) extension with the default renaming rule of _{%a_}{%y_}{%t}.

```bash
# Process a folder of PDFs
python 1_extract_paper_data.py /path/to/pdf_folder /path/to/output_folder

# Process a single PDF
python 1_extract_paper_data.py /path/to/paper.pdf /path/to/output_folder
```

### 2. Analyze with Claude (`2_analyze_with_claude.py`)

Uses Claude API to analyze the text files and generate summaries, research gaps, objectives, and keywords.

```bash
# Process all text files in a folder (skip files with existing analysis)
python 2_analyze_with_claude.py /path/to/text_folder

# Process all text files, overwriting existing analyses
python 2_analyze_with_claude.py /path/to/text_folder --overwrite
```

### 3. Create Markdown Files (`3_create_markdown.py`)

Converts the analyzed text files into standardized markdown files with YAML frontmatter.

```bash
# Process all text files in a folder (skip existing markdown files)
python 3_create_markdown.py /path/to/text_folder /path/to/markdown_folder

# Process all text files, overwriting existing markdown files
python 3_create_markdown.py /path/to/text_folder /path/to/markdown_folder --overwrite

# Process a single text file
python 3_create_markdown.py /path/to/paper.txt /path/to/markdown_folder
```

## Complete Workflow Example

```bash
# 1. Extract data from PDFs
python 1_extract_paper_data.py ~/research/papers ~/research/extracted

# 2. Analyze with Claude
python 2_analyze_with_claude.py ~/research/extracted

# 3. Create markdown files
python 3_create_markdown.py ~/research/extracted ~/research/markdown
```

## Markdown File Structure

The final markdown files have the following structure:

```markdown
---
title: Paper Title
author: Authors
year: Year
tags:
- keyword1
- keyword2
- ...
---

# TITLE
Paper Title

# AUTHOR
Authors

# SUMMARY
[Claude-generated summary]

# KEYWORDS
#keyword1, #keyword2, ...

# RESEARCH GAP/PROBLEM
[Claude-identified research gap]

# OBJECTIVES
[Claude-extracted objectives]

# ABSTRACT
[Abstract from Zotero or PDF]
```

## Notes

- File naming follows the pattern `Author_et_al_YEAR.txt` and `Author_et_al_YEAR.md`
- Keywords are standardized to singular form
- All markdown sections use H1 headings for consistency
- The scripts handle both single files and batches of files
- Use the `--overwrite` flag when you want to replace existing output files
- Cost considerations: Processing large volumes of papers with Claude API will incur costs based on your usage and Anthropic's pricing
