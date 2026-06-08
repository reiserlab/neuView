# Input Data Directory

This directory contains CSV data files that provide additional metadata and external references for neuView's neuron analysis pages. These files enhance the generated websites with brain region information, citation links, and multimedia content.

## File Overview

| File | Purpose | Records | Usage |
|------|---------|---------|-------|
| `brainregions.csv` | Brain region mappings | 165 | ROI abbreviation to full name translation |
| `citations.csv` | Scientific references | 41 | Synonym and research citation links |
| `youtube.csv` | Video content | 701 | YouTube video integration for neuron types |

## brainregions.csv

### Purpose
Maps brain region abbreviations to their full anatomical names for user-friendly display in generated websites.

### Format
```csv
ABBREVIATION, Full Name
```

### Examples
```csv
OL, Optic Lobe
LA, Lamina
ME, Medulla
AME, Accessory Medulla
LO, Lobula
LOP, Lobula Plate
MB, Mushroom Body
```

### Usage in neuView
- Loaded by `PageGenerator._load_brain_regions()`
- Used to translate ROI abbreviations in tables and visualizations
- Enhances readability of anatomical region references
- Fallback: If file missing or region not found, abbreviation is displayed as-is

### Data Requirements
- First comma separates abbreviation from full name
- Abbreviations should match those used in neuPrint database
- Full names can contain commas (parsing handles this)
- UTF-8 encoding required

## citations.csv

### Purpose
Provides citation information for scientific references linked to neuron synonyms and research papers.

### Format
```csv
Citation Key, DOI or URL, "Authors (YEAR):Paper Title"
```

The authors are listed with their full names, if possible. A good source for Authors list and the paper title seems to be https://openalex.org/.


### Examples
```csv
Lee 2002, 10.1080/01677060216292,"Gyunghee Lee, Jeffrey C. Hall, and Jae H. Park. (2002): Doublesex Gene Expression in the Central Nervous System of Drosophila melanogaster"
Kimura 2008, 10.1016/j.bbrc.2008.05.003,"Shuhei Kimura, Shun Sawatsubashi, Saya Ito, Alexander Kouzmenko, Eriko Suzuki, Yue Zhao, Kaoru Yamagata, Masahiko Tanabe, Takuya Murata, Hiroyuki Matsukawa, Ken-ichi Takeyama, Nobuo Yaegashi, and Shigeaki Kato (2008): Drosophila arginine methyltransferase 1 (DART1) is an ecdysone receptor co-repressor"
```

### Usage in neuView
- Loaded by `PageGenerator._load_citations()`
- Used in `_process_synonyms()` to create clickable citation links
- DOI strings (starting with "10.") automatically converted to full URLs
- Referenced by neuron synonym data for scientific validation

### Data Requirements
- Citation key: Unique identifier (typically "Author Year")
- DOI/URL: Either DOI (e.g., "10.1080/01677060216292") or full URL
- Title: Complete paper title in quotes to handle commas
- CSV parsing handles quoted titles with internal commas
- UTF-8 encoding required

### DOI Processing
- DOI entries starting with "10." are automatically prefixed with "https://doi.org/"
- Full URLs are used as-is
- Invalid or missing DOIs fall back to "#" placeholder

### One way to acquire data
- search for key + "Drosophila" on https://scholar.google.com find DOI
- copy key + DOI to citations.csv
- search for DOI on https://openalex.org
- copy list of authors. Add "and" before last author. Add year and title to citations.csv

## youtube.csv

### Purpose
Maps neuron types to YouTube video content for enhanced visualization and educational resources.

### Format
```csv
Video ID, Description/Neuron Type Name
```

### Examples
```csv
RW9sMtmrz2g,VPN groups
ys7q1MVbSP4,Different patterns of sampling visual space in the Drosophila visual system
3Gvpj9ghnH4,Regions of the Drosophila visual system and 15 columnar cell types
qiy3ZLzfq5E,LT74, a Drosophila Visual Projection Neuron from optic-lobe:v1.0 (short)
```

### Usage in neuView
- Loaded by `PageGenerator._load_youtube_videos()`
- Used by `_find_youtube_video()` to match neuron types with video content
- Videos only displayed for right hemisphere neuron pages
- Case-insensitive matching against neuron type names in descriptions

### Data Requirements
- Video ID: 11-character YouTube video identifier
- Description: Should contain neuron type name for matching
- Matching algorithm searches for neuron type name within description
- Only applied to right soma side pages to avoid duplication

### Video Integration
- Matched videos appear as embedded links in neuron pages
- Full YouTube URLs generated: `https://www.youtube.com/watch?v={video_id}`
- Enhances pages with visual demonstrations and educational content
- Graceful degradation: No video links shown if no matches found

## File Management

### Location
All CSV files must be located in the `neuview/input/` directory relative to the project root.

### Encoding
- All files must use UTF-8 encoding
- Handles international characters and special symbols
- Consistent with web standards and database content

### Error Handling
- Missing files: Applications continue with reduced functionality
- Malformed entries: Individual problematic lines are skipped
- Empty files: Treated as no data available
- Detailed logging for troubleshooting

### Loading Process
Files are loaded during `PageGenerator` initialization:
1. Brain regions loaded first for ROI translation
2. Citations loaded for reference linking
3. YouTube mappings loaded on-demand per neuron type

## Maintenance Guidelines

### Adding New Entries

**Brain Regions:**
```csv
NEW_ABBREV, New Region Full Name
```

**Citations:**
```csv
Author YYYY, DOI_or_URL, "Complete Paper Title"
```

**YouTube Videos:**
```csv
video_id_123, Neuron Type Name or Description
```

### Data Validation
- Verify CSV syntax and encoding
- Test abbreviations match neuPrint database ROIs
- Validate DOIs resolve to correct papers
- Confirm YouTube video IDs are accessible
- Check for duplicate entries

### Performance Considerations
- Files loaded once during initialization
- In-memory lookup for fast access during page generation
- Large files (>10,000 entries) may impact startup time
- Consider data structure optimization for very large datasets

## Integration with neuView

### Code Integration Points
- `PageGenerator.__init__()`: Loads all CSV data during initialization
- `_load_brain_regions()`: Processes brain region mappings
- `_load_citations()`: Handles citation data with DOI conversion
- `_load_youtube_videos()`: Creates neuron type to video mappings
- `_find_youtube_video()`: Matches neuron types to available videos

### Template Usage
- Brain regions: Used in ROI tables and region analysis sections
- Citations: Linked from neuron synonym displays
- YouTube: Embedded as video links in neuron pages

### Configuration Dependencies
- No configuration file settings required
- Automatic detection and loading
- Graceful handling of missing or incomplete data

## Troubleshooting

### Common Issues

**File Not Found:**
- Ensure files are in correct `neuview/input/` location
- Check file permissions are readable
- Verify filename spelling and case

**Encoding Errors:**
- Save files as UTF-8 encoding
- Avoid Excel default CSV export (may use wrong encoding)
- Use text editor that preserves UTF-8

**Parsing Errors:**
- Check CSV format with quoted titles for commas
- Ensure no trailing spaces or invisible characters
- Validate each line has correct number of columns

**Missing Links:**
- Citations: Verify citation keys match those used in neuron data
- YouTube: Ensure descriptions contain recognizable neuron type names
- Brain regions: Check abbreviations match neuPrint ROI names

### Debugging
Enable verbose logging to see detailed file loading information:
```bash
neuview generate --verbose
```

Check logs for specific error messages about file loading and data parsing issues.
