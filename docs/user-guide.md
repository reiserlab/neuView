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

You need a NeuPrint authentication token:

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

scatter:
  # Minimum column count threshold for data quality filtering
  # Data points with cols_innervated <= this value will be excluded from scatter plots
  # Set to null to disable this filter
  min_col_count_threshold: null
```

### Scatter Plot Configuration

Configure scatter plot generation for optic lobe datasets:

```yaml
scatter:
  min_col_count_threshold: 9.0  # Default threshold
```

**Configuration Options:**
- `min_col_count_threshold`: Minimum number of columns a neuron type must innervate to be included in scatter plots
  - Default: `9.0` (excludes types with ≤ 9 columns)
  - Set to `null` to disable filtering and include all data points
  - This filter helps exclude low-quality or sparse data from visualizations
  - Can be overridden per-command using `--min-col-count` CLI option

**Use Cases:**
- **Strict quality control** (default 9.0): Only well-sampled types with sufficient column coverage
- **Relaxed filtering** (e.g., 5.0): Include more types with moderate column coverage
- **No filtering** (null): Include all types regardless of column count

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

# Generate scatter plots (for optic lobe datasets)
pixi run neuview create-scatter

# Generate scatter plots with custom quality threshold
pixi run neuview create-scatter --min-col-count 5

# Generate scatter plots without quality filtering
pixi run neuview create-scatter --min-col-count -1

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

**`inspect` command:**
- `neuview inspect <type>` - Show detailed information about a neuron type
- Displays: neuron count, soma distribution, connectivity stats

**`create-scatter` command:**
- `neuview create-scatter` - Generate SVG scatter plots of spatial metrics for optic lobe types
- `--min-col-count <value>` - Set minimum column count threshold for data quality filtering
  - Default: 9.0 (excludes points with cols_innervated ≤ 9)
  - Set to -1 to disable filtering
  - Can also be configured in `config.yaml` under `scatter.min_col_count_threshold`
- Generates plots for ME, LO, and LOP regions
- Creates both combined (both hemispheres) and hemisphere-specific (L/R) plots
- Output: `output/scatter/*.svg` files

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

**JavaScript example:**
```javascript
fetch('https://your-site.com/data/neurons.json')
  .then(r => r.json())
  .then(data => {
    console.log('Total neurons:', data.names.length);
    console.log('Neurons:', data.neurons);
  });
```

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

### Common Issues

**"No neuron types found"**
- Check NeuPrint credentials in `.env`
- Verify dataset name matches exactly
- Test connection: `pixi run neuview test-connection`
- Check network connectivity

**"Template rendering failed"**
- Check for syntax errors in custom templates
- Verify all required template variables present
- Look at verbose output: `--verbose` flag

**"Cache issues"**
- Clear cache: `pixi run neuview build --clear-cache`
- Check cache directory permissions
- Verify sufficient disk space

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

```bash
# Verbose output
pixi run neuview build --verbose

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

### Environment Variables

- `NEUPRINT_APPLICATION_CREDENTIALS` - NeuPrint auth token (required)
- `NEUVIEW_CONFIG_PATH` - Custom config file path
- `NEUVIEW_CACHE_DIR` - Custom cache directory
- `NEUVIEW_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `NEUVIEW_OUTPUT_DIR` - Override output directory

### Performance Tips

**For large datasets:**
- Enable caching (default)
- Use parallel generation
- Increase max_workers if you have CPU cores
- Generate subsets first for testing

**For faster iterations:**
- Don't clear cache unless necessary
- Use `--types` flag to regenerate specific pages
- Disable HTML minification during development
- Use subsets for testing changes

**Cache management:**
- Cache stored in `.neuview_cache/` by default
- Safe to delete - will regenerate from NeuPrint
- Old cache automatically cleaned
- No manual maintenance needed

### Data Citation

When using neuView-generated websites, cite:

1. **The dataset:** Check NeuPrint for proper citation
2. **neuView tool:** (If publishing using neuView)
3. **Original data sources:** Listed in connectivity tables

**Example citation:**
```
Neuron visualizations generated using neuView (https://github.com/your-org/neuview).
Data from NeuPrint (https://neuprint.janelia.org), 
Hemibrain dataset v1.2.1 (Scheffer et al., 2020).
```

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
