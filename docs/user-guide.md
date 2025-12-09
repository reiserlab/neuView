# neuView User Guide

A comprehensive guide for users of the neuView neuron visualization platform.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Generated Website Features](#generated-website-features)
- [Search Functionality](#search-functionality)
- [Dataset-Specific Features](#dataset-specific-features)
- [Understanding the Interface](#understanding-the-interface)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

## Quick Start

```bash
# Install dependencies
pixi install

# Set up environment (creates .env file)
pixi run setup-env

# Edit .env file with your NeuPrint token
# NEUPRINT_APPLICATION_CREDENTIALS=your_token_here

# Test connection
pixi run neuview test-connection

# Generate website
pixi run neuview build
```

Your website will be in the `output/` directory. Open `output/index.html` in a browser.

## Installation

### Prerequisites

- Python 3.11 or higher
- pixi package manager ([installation guide](https://pixi.sh))
- NeuPrint access token
- Git for version control

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd neuview
   ```

2. **Install dependencies:**
   ```bash
   pixi install
   ```

3. **Set up environment:**
   ```bash
   pixi run setup-env
   ```
   
   This creates a `.env` file. Edit it to add your NeuPrint token:
   ```
   NEUPRINT_APPLICATION_CREDENTIALS=your_token_here
   ```

4. **Test connection:**
   ```bash
   pixi run neuview test-connection
   ```

### Setting Up Authentication

**Option 1: Environment File (Recommended with pixi)**
**Authentication Methods**:
1. **Environment file**: Run `pixi run setup-env`, then edit `.env` with your token
2. **Environment variable**: `export NEUPRINT_TOKEN="your-token-here"`

1. Go to your NeuPrint server (e.g., https://neuprint.janelia.org)
2. Click "Account" → "Auth Token"
3. Copy the token
4. Add to `.env` file or set as environment variable:
   ```bash
   export NEUPRINT_APPLICATION_CREDENTIALS="your_token_here"
   ```

## Configuration

### Basic Configuration

Edit `config.yaml` to configure your build:

```yaml
neuprint:
  server: neuprint.janelia.org
  dataset: optic-lobe:v1.0

html:
  title_prefix: "Optic Lobe"
  github_repo: "https://github.com/your-repo"
  youtube_channel: "https://youtube.com/your-channel"

performance:
  max_workers: 4
  cache_enabled: true
```

### Dataset-Specific Configurations

Different datasets may require specific settings:

```yaml
# For CNS dataset
neuprint:
  server: neuprint.janelia.org
  dataset: hemibrain:v1.2.1

# For FAFB/FlyWire dataset
neuprint:
  server: flywire.ai
  dataset: production
```

### Neuron Type Subsets

You can generate pages for a subset of neuron types:

```yaml
subsets:
  small-test:
    neuron_types:
      - "Tm3"
      - "Mi1"
      - "T4"
    generate_index: true
    
  medium-sample:
    max_types: 50
    randomize: true
    generate_index: true
```

Use subsets with:
```bash
pixi run neuview build --subset small-test
```

## Basic Usage

### Essential Commands

```bash
# Generate complete website
pixi run neuview build

# Generate with cache clearing
pixi run neuview build --clear-cache

# Inspect a specific neuron type
pixi run neuview inspect "Tm3"

# Generate for specific neuron types
pixi run neuview build --types "Tm3,Mi1,T4"

# Use a subset from config
pixi run neuview build --subset small-test

# Verbose output for debugging
pixi run neuview build --verbose
```

### Command Options

**`build` command:**
- `--clear-cache` - Clear all caches before building
- `--types <list>` - Comma-separated list of neuron types
- `--subset <name>` - Use a predefined subset from config
- `--parallel` - Enable parallel processing
- `--verbose` - Detailed logging output
- `--output <dir>` - Custom output directory

### Neuron Type Inspection

Get detailed information about specific neuron types:

**Neuron Type Details**:
Use the `inspect` command to get detailed information about specific neuron types:
```bash
pixi run neuview inspect Dm4
```

## Advanced Features

### Batch Processing with Queue System

Process multiple neuron types efficiently using the queue system:

**Queue Operations**:
- Add single type: `pixi run neuview fill-queue --neuron-type Dm4`
- Add all types: `pixi run neuview fill-queue --all`
- Process queue: `pixi run neuview pop`
- View queue status: `ls -la output/.queue/`
- Clear queue: `rm -rf output/.queue/`

### Automatic Page Generation

neuView automatically detects available soma sides and generates all appropriate pages:

**Automatic Page Generation**:
- Multi-hemisphere data: Creates individual hemisphere pages (Dm4_L.html, Dm4_R.html) plus combined view (Dm4.html)
- Single-hemisphere data: Creates only the relevant side-specific page
- Detection happens automatically based on your neuron data distribution

**Automatic Detection Logic**:
- **Multiple hemispheres**: Creates individual side pages + combined page
- **Single hemisphere**: Creates only the relevant side page
- **Mixed data**: Handles unknown/unassigned soma sides intelligently
- **No user intervention required**: System analyzes data and creates optimal page set

### Citation Management

neuView automatically tracks missing citations and logs them for easy maintenance:

**Citation Management Commands**:
- Check missing citations: `cat output/.log/missing_citations.log`
- Monitor in real-time: `tail -f output/.log/missing_citations.log`
- Count unique missing: Use grep and sort commands on the log file

**Adding Missing Citations**: Add entries to `input/citations.csv` in format: `citation_key,DOI,display_text`

**Citation Log Features**:
- **Automatic Tracking**: Missing citations logged during page generation
- **Context Information**: Shows which neuron type and operation encountered missing citation
- **Rotating Logs**: Files rotate at 1MB (keeps 5 backups)
- **Timestamped Entries**: Each entry includes timestamp of missing citation encounter

### Verbose Mode and Debugging

Get detailed information about processing:

**Verbose Mode Commands**:
- Enable verbose output: `pixi run neuview --verbose generate -n Dm4`
- Enable debug mode: Use the `--verbose` flag for detailed logging

## Generated Website Features

### Interactive Index Page

The landing page (`index.html`) includes:

- **Quick Search**: Real-time autocomplete search with synonym support
- **Featured Types**: Highlighted neuron types
- **Statistics**: Dataset overview and neuron counts
- **Navigation**: Links to types list and help pages

**Quick Search:**
- Type to see autocomplete suggestions
- Searches neuron names, synonyms, and FlyWire types
- Click a result to navigate to that neuron type
- Keyboard navigation: ↑↓ arrows, Enter to select, Esc to close

### Individual Neuron Type Pages

Each neuron type has dedicated pages showing:

**Overview Section:**
- Neuron type name and description
- Cell count and soma distribution
- Synonyms and alternative names
- FlyWire type identifiers

**Connectivity Tables:**
- Upstream partners (inputs)
- Downstream partners (outputs)
- Connection weights and synapse counts
- Coefficient of Variation (CV) showing connection variability
- Neurotransmitter information

**ROI (Brain Region) Information:**
- Synapse distribution across brain regions
- Input/output counts per region
- Interactive region selection

**Neuroglancer Integration:**
- 3D visualization links
- Interactive neuron selection
- ROI overlay capabilities

### Interactive Features

**Search:**
- Header search bar on all pages
- Real-time autocomplete
- Searches by: neuron name, synonym, FlyWire type
- Side-specific navigation (L/R/Combined)

**Filtering (Types Page):**
- Filter by cell count
- Filter by neurotransmitter
- Filter by brain regions
- Text search across all fields
- Tag-based filtering (synonyms, FlyWire types)

**Neuroglancer:**
- Click checkboxes to add neurons to 3D viewer
- Select multiple connectivity partners
- Toggle ROI visibility
- Automatic URL generation for sharing

## Search Functionality

### How Search Works

The search system loads neuron data from JSON (or JavaScript fallback) and provides instant autocomplete suggestions.

**Data Sources:**
- **Primary**: `data/neurons.json` - Used when served from web server
- **Fallback**: `data/neurons.js` - Used when opening local files

### Search Features

**Searches across:**
1. **Neuron names** (e.g., "AN07B013")
2. **Synonyms** (e.g., "Cachero 2010: aSP-j")
3. **FlyWire types** (e.g., "CB3127")

**Smart matching:**
- Exact match (highest priority)
- Starts with query
- Contains query
- Synonym author/year matching
- Synonym name-only matching

**Example:** For neuron "AOTU001" with synonym "Cachero 2010: aSP-j"
- Typing "aotu" → matches name
- Typing "cachero" → matches synonym author
- Typing "asp-j" → matches synonym name

### Using Search

**On any page:**
1. Click in the search box
2. Start typing (minimum 2 characters)
3. See autocomplete dropdown
4. Use ↑↓ arrows to navigate
5. Press Enter or click to select
6. Navigate to neuron page

**Side selection:**
- Some neurons show (L, R, M) links
- Click to go directly to that hemisphere
- Combined page shows all hemispheres

### Search Data Format

The search uses a structured JSON format:

```json
{
  "names": ["AN07B013", "AOTU001", ...],
  "neurons": [
    {
      "name": "AN07B013",
      "urls": {
        "combined": "AN07B013.html",
        "left": "AN07B013_L.html",
        "right": "AN07B013_R.html"
      },
      "types": {
        "flywire": ["AN_GNG_60"],
        "synonyms": ["Cachero 2010: aSP-j"]
      }
    }
  ]
}
```

### Accessing Search Data Externally

External services can access the neuron data:

**Python example:**
```python
import requests

response = requests.get('https://your-site.com/data/neurons.json')
data = response.json()

# Get all neuron names
names = data['names']

# Find neurons with specific FlyWire type
neurons_with_type = [
    n for n in data['neurons']
    if n.get('types', {}).get('flywire', []) == ['CB3127']
]
```

##### Best Practices

1. **Start Broad**: Use basic filters first to narrow down the dataset
2. **Combine Strategically**: Combine complementary filters (e.g., ROI + neurotransmitter)
3. **Use Tag Filters for Discovery**: Use synonym/Flywire filters to find cross-referenced types
4. **Check Filter Status**: Always verify which filters are active via visual indicators

This comprehensive filtering system helps researchers quickly identify neuron types that have been cross-referenced with external databases or have alternative naming information available, making data exploration and comparative analysis more efficient.

**Navigation**:
- Breadcrumb navigation for easy orientation
- Quick neuron type switcher in header
- Cross-referenced links between related neurons
- Mobile-friendly hamburger menus

## Dataset-Specific Features

### FAFB (FlyWire) Dataset

**Special behaviors:**
- Uses `side` property instead of `somaSide`
- Different Neuroglancer template
- ROI checkboxes automatically disabled
- FlyWire-specific visualizations

**Configuration:**
```yaml
neuprint:
  server: flywire.ai
  dataset: production
```

### CNS, Hemibrain, and Optic-Lobe Datasets

**Standard features:**
- Full ROI visualization support
- Standard Neuroglancer integration
- Hemisphere-specific pages (L/R)
- Combined views for bilateral types

**Configuration:**
```yaml
neuprint:
  server: neuprint.janelia.org
  dataset: hemibrain:v1.2.1  # or cns:v1.0, optic-lobe:v1.0
```

### Dataset Detection

The system automatically detects dataset type and adjusts:
- Property names for data extraction
- Neuroglancer template selection
- ROI visualization capabilities
- Page generation logic

## Understanding the Interface

### ROI (Region of Interest) Features

**ROI Tables show:**
- Brain regions where neurons have synapses
- Input (upstream) and output (downstream) counts
- Relative distribution across regions

**Neuroglancer ROI Checkboxes:**
- Available for CNS/Hemibrain/Optic-lobe datasets
- Disabled for FAFB (not supported)
- Click to overlay regions in 3D viewer
- Multiple regions can be selected

**ROI Data:**
- Dynamically loaded from authoritative sources
- Cached locally for performance
- Automatically updated with dataset changes

### Connectivity Tables

**Understanding the columns:**

| Column | Description |
|--------|-------------|
| Partner Type | Name of connected neuron type |
| # | Number of individual partner neurons |
| Total Weight | Sum of all connections |
| Avg. Weight | Average connections per neuron |
| CV | Coefficient of Variation (connection consistency) |
| NT | Primary neurotransmitter |

**Coefficient of Variation (CV):**
- Shows connection variability
- CV = (standard deviation / mean) × 100
- Low CV (0-30): Consistent connections
- Medium CV (30-70): Moderate variation
- High CV (70+): Some partners much stronger

**Neurotransmitter Abbreviations:**
- ACH: Acetylcholine
- GABA: Gamma-aminobutyric acid
- GLU: Glutamate
- DA: Dopamine
- 5HT: Serotonin
- OCT: Octopamine

### Neuroglancer Integration

**Opening in Neuroglancer:**
1. Click "Open in Neuroglancer" button
2. 3D viewer opens with the neuron highlighted
3. Use checkboxes to add connectivity partners
4. Select ROIs to visualize regions

**Checkbox features:**
- Empty bodyIds → Checkbox disabled
- Self-reference detection → Prevents duplicates
- Multiple selection → Build complex views
- URL updates automatically

**Tips:**
- Start with just the main neuron
- Add partners one at a time
- Use ROI overlays sparingly
- Save URLs to share specific views

### Understanding the Data

**Neuron Counts:**
- Total count includes all hemispheres
- L/R counts show distribution
- Unknown soma side may exist

**Connection Weights:**
- Weight = number of synapses
- Higher weight = stronger connection
- Directional: upstream vs downstream

**Soma Sides:**
- L: Left hemisphere
- R: Right hemisphere
- M: Middle/central
- Combined pages show all

## Troubleshooting

### Citation Issues

**Missing Citations in Pages**

If you notice citations are missing or showing as broken links:

1. Check the citation log file: `cat output/.log/missing_citations.log`

2. Add missing citations to `input/citations.csv` in format: `citation_key,DOI,display_text`

3. Regenerate affected pages: `pixi run neuview generate -n YourNeuronType`

**Citation Log File Not Created**

If `output/.log/missing_citations.log` doesn't exist:
- Ensure the output directory is writable
- Check that pages are being generated (citations are only logged during generation)
- Verify that there are actually missing citations to log

**Large Citation Log Files**

Citation logs automatically rotate when they reach 1MB:
- Up to 5 backup files are kept (`.log.1`, `.log.2`, etc.)
- Check for repeated missing citations that should be added to `citations.csv`

### Common Issues

**Authentication Problems**
**Connection Troubleshooting Commands**:
- Verify token: `echo $NEUPRINT_TOKEN`
- Test connection: `pixi run neuview test-connection`
- Check network connectivity

**"Template rendering failed"**
- Check for syntax errors in custom templates
- Verify all required template variables present
- Look at verbose output: `--verbose` flag

**Performance Issues**
**Performance Issue Commands**:
- Check output directory for cached files: `ls -la output/.cache/`
- Clear corrupted cache: `rm -rf output/.cache/`
- Enable performance monitoring: Use `--verbose` flag for detailed operation logs

**Search not working:**
- Open browser console (F12)
- Check for JavaScript errors
- Verify `neurons.json` and `neurons.js` exist in `output/data/`
- Check data source in console: `window.neuronSearch.dataSource`

**Page generation slow:**
- Enable caching (default)
- Reduce parallelization if memory constrained
- Use subsets for testing
- Check NeuPrint server response time

### Debug Mode

Enable detailed logging:

**Debug Mode Setup**: Run `pixi run neuview --verbose generate -n Dm4`

# Or set environment variable
export NEUVIEW_LOG_LEVEL=DEBUG
pixi run neuview build
```

Check log output for:
- Data fetching progress
- Cache hit/miss information
- Template rendering steps
- Error stack traces

### Browser Compatibility

**Recommended browsers:**
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Known issues:**
- IE 11: Not supported
- Older browsers: May lack ES6 support
- Mobile browsers: Limited Neuroglancer support

**JavaScript requirements:**
- ES6 features (async/await, fetch, promises)
- localStorage for preferences
- Dynamic script loading for search fallback

### Getting Help

**Before reporting issues:**
1. Check this guide's troubleshooting section
2. Run with `--verbose` flag
3. Check browser console for errors
4. Verify configuration file syntax

**Information to include:**
- neuView version
- Dataset name and version
- Error messages (full stack trace)
- Configuration file (without tokens)
- Browser and version

## Reference

### File Organization

```
output/
├── index.html              # Landing page with search
├── types.html              # Neuron type listing
├── help.html               # Help documentation
├── data/
│   ├── neurons.json        # Search data (JSON format)
│   └── neurons.js          # Search data (JS fallback)
├── types/
│   ├── Tm3.html           # Individual neuron pages
│   ├── Tm3_L.html         # Left hemisphere
│   └── Tm3_R.html         # Right hemisphere
└── static/
    ├── js/
    │   └── neuron-search.js  # Search functionality
    ├── css/
    │   └── *.css             # Stylesheets
    └── icons/
        └── *.svg             # Icons
```

### Configuration Reference

**Complete config.yaml example:**

```yaml
neuprint:
  server: neuprint.janelia.org
  dataset: hemibrain:v1.2.1

html:
  title_prefix: "Hemibrain"
  github_repo: "https://github.com/your-org/your-repo"
  youtube_channel: "https://youtube.com/@yourchannel"
  fathom_id: "YOUR_FATHOM_ID"  # Optional analytics

output:
  directory: "output"
  clean_before_build: false

performance:
  max_workers: 4
  cache_enabled: true
  parallel_generation: true

templates:
  minify_html: true
  minify_js: false
  minify_css: false

discovery:
  max_types: 100
  randomize: false
  exclude_types:
    - "test_type"
    - "incomplete_type"

subsets:
  small:
    neuron_types:
      - "Tm3"
      - "Mi1"
    generate_index: true
```

**Analytics Integration**:
- **Fathom Analytics**: Add your Fathom site ID to enable privacy-focused analytics
- The analytics script is automatically included on all generated pages when configured
- No additional setup required - just uncomment and set your site ID

### Command Reference

neuView provides a comprehensive command-line interface. All commands are run with the `pixi run neuview` prefix.

#### Available Commands

**`generate`** - Generate HTML pages for neuron types
- Options: `--neuron-type`, `--output-dir`, `--image-format`, `--embed/--no-embed`, `--minify/--no-minify`
- Example: `pixi run neuview generate --neuron-type Tm3`

**`inspect`** - Inspect detailed information about a specific neuron type
- Shows: neuron counts, soma sides, synapse statistics, bilateral ratio
- Example: `pixi run neuview inspect Dm4`

**`test-connection`** - Test connection to NeuPrint server
- Options: `--detailed`, `--timeout`
- Example: `pixi run neuview test-connection --detailed`

**`fill-queue`** - Create YAML queue files for batch processing
- Options: `--neuron-type`, `--all`, `--output-dir`, `--image-format`, `--embed/--no-embed`
- Example: `pixi run neuview fill-queue --all`

**`pop`** - Process a single queue file
- Options: `--output-dir`, `--minify/--no-minify`
- Example: `pixi run neuview pop`

**`create-list`** - Generate index page with all neuron types
- Options: `--output-dir`, `--minify/--no-minify`
- Example: `pixi run neuview create-list`

#### Global Options

- `-c, --config` - Path to configuration file
- `-v, --verbose` - Enable verbose output and DEBUG logging
- `--version` - Show version and exit
- `--help` - Show help message

For detailed command options and examples, see the developer guide.

### Performance Tips

1. **Use Caching**: Cache provides up to 97.9% speed improvement on subsequent runs
2. **Process in Batches**: Use queue system for multiple neuron types
3. **Clean Cache Periodically**: Remove cache files with `rm -rf output/.cache/` when needed
4. **Monitor Progress**: Use verbose mode for long-running operations
5. **Optimize Configuration**: Adjust cache settings based on available memory

### Data Citation

When using neuView-generated data in publications:

**Required Citations**:
1. **Original neuPrint database** and dataset version
2. **neuView version** used for generation
3. **Generation date** of the catalog
4. **Specific filtering** or configuration applied

**Example Citation**:
**Citation Example**: "Neuron data analysis generated using neuView from neuPrint database (neuprint.janelia.org), dataset: hemibrain v1.2.1, catalog generated: 2024-01-15. Connectivity data from Scheffer et al. (2020). ROI analysis performed using standard neuView configuration with automatic hemisphere detection."

### Environment Variables

**Currently Implemented:**

- **`NEUPRINT_TOKEN`** - NeuPrint API token (required)
  - Example: `your-token-string`
  - Set in `.env` file or as environment variable
  - Required for all database operations

### Keyboard Shortcuts

**Search:**
- Type to activate
- ↑/↓ arrows to navigate
- Enter to select
- Esc to close

**Browser:**
- Ctrl/Cmd + F: Find in page
- Ctrl/Cmd + Click: Open link in new tab

### Frequently Asked Questions

**Q: Can I use this offline?**
A: Yes! Open `output/index.html` directly. Search works via JavaScript fallback.

**Q: How do I share the website?**
A: Upload the `output/` folder to any web server or GitHub Pages.

**Q: Can I customize the styling?**
A: Yes. Edit templates in `templates/` and CSS in `static/css/`.

**Q: How often should I rebuild?**
A: When dataset updates, or when you want to include new neuron types.

**Q: Does search work offline?**
A: Yes. It uses `neurons.js` fallback for local file access.

**Q: Can I add custom neuron types?**
A: Currently only NeuPrint datasets are supported. Manual additions require code changes.

**Q: How do I update to a new dataset version?**
A: Update `config.yaml` with new dataset name, clear cache, rebuild.

**Q: Can external services access the neuron data?**
A: Yes! The `data/neurons.json` file is a standard JSON API endpoint.

**Q: What's the difference between neurons.json and neurons.js?**
A: Same data, different formats. JSON for web servers/APIs, JS for local file access.

**Q: Why do some neurons have L/R pages and others don't?**
A: Automatically determined by soma distribution. Bilateral neurons get separate pages.
