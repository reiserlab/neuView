# neuView User Guide

A comprehensive guide for users of neuView, a modern Python CLI tool that generates interactive HTML pages for neuron types using data from NeuPrint. This guide covers installation, configuration, usage, and troubleshooting for all supported datasets.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Generated Website Features](#generated-website-features)
- [Dataset-Specific Features](#dataset-specific-features)
- [Understanding the Interface](#understanding-the-interface)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

## Quick Start

Get up and running with neuView in minutes:

1. **Install neuView**: Clone repository and run `pixi install`

2. **Configure your connection**: Run `pixi run setup-env` and add your NeuPrint token to `.env`

3. **Generate your first page**: `pixi run neuview generate -n Dm4`

4. **View the results**:
   Open `output/types/Dm4.html` in your browser to see your interactive neuron catalog

5. **Generate a complete set of pages**: `pixi run subset-medium`

6. **View the start page**: Open `output/index.html` in your browser.

## Installation

### Prerequisites

- **pixi** package manager ([installation guide](https://pixi.sh/latest/))
- **Git** for cloning the repository
- **NeuPrint access token** (get from [neuprint.janelia.org](https://neuprint.janelia.org/account))

### Installation Steps

**Installation Steps**:
1. Clone the repository and navigate to directory (`git clone https://github.com/reiserlab/neuview; cd neuview`)
2. [Optional]: Install dependencies: `pixi install`
3. Verify installation: `pixi run neuview --version` and `pixi run neuview --help`

### Setting Up Authentication

**Option 1: Environment File (Recommended with pixi)**
**Authentication Methods**:
1. **Environment file**: Run `pixi run setup-env`, then edit `.env` with your token
2. **Environment variable**: `export NEUPRINT_TOKEN="your-token-here"`

**Getting Your Token**:
1. Visit [neuprint.janelia.org](https://neuprint.janelia.org/account)
2. Log in with your Google account
3. Click on your profile icon → "Account"
4. Copy your "Auth Token"

## Configuration

### Basic Configuration

neuView uses a `config.yaml` file for project settings. Each project generates a set of output files for the specified dataset. A default configuration is included:

**Basic Configuration** - See `config.yaml` for complete structure:
- **neuprint**: Server, dataset, and token configuration
- **output**: Directory settings and JSON generation options
- **html**: Title prefix and connectivity inclusion settings

### Dataset-Specific Configurations

neuView includes pre-configured settings for different datasets:

- `config/config.cns.yaml` - Central Nervous System dataset
- `config/config.optic-lobe.yaml` - Optic Lobe dataset
- `config/config.fafb.yaml` - FAFB (FlyWire) dataset
- `config/config.example.yaml` - Template configuration

Use a specific configuration, create a symlink or copy with the name `config.yaml` in the project directory.

#### Usage Example

**Configuration Example** - `config.yaml`:
Dataset aliases like `male-cns:v0.9` automatically resolve to appropriate adapters (CNS in this case). See configuration reference for complete examples.

This configuration will work seamlessly without any warnings. The system automatically:
- Recognizes `male-cns:v0.9` as a CNS dataset
- Uses the appropriate CNS adapter
- Handles all CNS-specific database queries correctly

### Auto-Discovery Configuration

If no additional parameters are given, the command `neuview fill-queue` uses an auto-discovery mechanism to determine which neuron types to include in the queue. Configure automatic neuron type discovery settings:

**Discovery Settings** - Add under `discovery` section in `config.yaml`:
- `max_types` (default: 10): Maximum number of neuron types to discover
- `type_filter` (optional): Regex pattern to filter neuron type names
- `exclude_types` (optional): List of neuron types to exclude from discovery
- `include_only` (optional): If specified, only include these specific types
- `randomize` (default: true): Randomize selection vs alphabetical order

**Example Configuration:**
```yaml
discovery:
  max_types: 15
  type_filter: "^(T|L)"  # Only types starting with T or L
  exclude_types:
    - "Test_Type"
    - "Debug_Neuron"
  randomize: false  # Use alphabetical order
```

### Neuron Type Subsets

For testing and batching purposes, you can define neuron type subsets in your `config.yaml`:

> **Note**: Neuron type selection is done through CLI options (e.g., `--neuron-type`) rather than configuration files. Use the command-line interface to specify which neuron types to process.
```yaml
subsets:
  subset-medium:
    - "SAD103"
    - "Tm3"
    - "AOTU019"
  subset-small:
    - "SAD103"
    - "Tm3"
```

## Basic Usage

### Essential Commands

**Basic Commands**:
- Test connection: `pixi run neuview test-connection`
- Generate single page: `pixi run neuview generate -n Dm4`
- Generate index page: `pixi run neuview create-list`
- Generate a subset including index page: `pixi run subset-medium`
- Generate all pages: `pixi run neuview fill-queue --all` then process with `pixi run neuview pop` or use the pixi shortcut task `pixi run create-all-pages`

### Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `-n, --neuron-type` | Specify neuron type | `-n Dm4` |
| `--image-format` | Image format for grids | `--image-format svg` |
| `--embed/--no-embed` | Embed images in HTML | `--embed` |
| `--minify/--no-minify` | HTML minification | `--no-minify` |
| `-c, --config` | Use custom config | `-c config.yaml` |
| `--verbose` | Enable detailed output | `--verbose` |

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

The main `index.html` provides:

- **Real-time search** with autocomplete for neuron types
- **Advanced filtering** by cell count, neurotransmitter, brain region
- **Interactive cell count tags** - click to filter by count ranges
- **Automatic hemisphere detection** - generates appropriate pages for available data
- **Responsive design** for mobile and desktop
- **Export functionality** for filtered results

### Individual Neuron Type Pages

Each neuron type page includes comprehensive information:

**Summary Statistics**:
- Cell counts by hemisphere (L, R, combined)
- Neurotransmitter predictions with confidence scores
- Brain region innervation summary
- Morphological classifications

**3D Visualization**:
- Direct links to Neuroglancer with pre-loaded neuron data
- Interactive 3D neuron models
- Layer-by-layer anatomical analysis
- Coordinate system integration

**Connectivity Analysis**:
- Input/output connection tables with partner details
- Connection strength metrics and statistics
- Partner neuron links for cross-referencing
- Hemisphere-specific connectivity patterns

**Spatial Coverage**:
- Hexagonal grid visualizations showing neuron distribution
- Brain region distribution maps
- Hemisphere comparison views
- ROI (Region of Interest) innervation analysis

### Interactive Features

**Data Tables**:
- Sortable columns for all data types
- Searchable content with real-time filtering
- Pagination controls for large datasets
- Exportable data in multiple formats

**Filtering Controls**:
- Connection strength sliders for fine-tuning
- Brain region selections with hierarchical organization
- Hemisphere toggles (L/R/Combined)
- Cell count range selectors
- **Synonym and Flywire Type Filtering**: Click on synonym tags (blue) or Flywire type tags (green) to filter neuron types by additional naming information

#### Advanced Filtering System

The Types page provides comprehensive filtering capabilities through multiple mechanisms designed for efficient neuron type exploration.

##### Basic Filters

Available through dropdown controls:

- **ROI (Region of Interest)**: Filter by brain regions where neurons are found
- **Neurotransmitter**: Filter by consensus or predicted neurotransmitter type
- **Dimorphism**: Filter by sexual dimorphism characteristics
- **Cell Class Hierarchy**: Filter by superclass, class, or subclass
- **Soma Side**: Filter by hemisphere (left, right, middle, undefined)

##### Tag-Based Filters

Advanced filters activated by clicking colored tags within neuron type cards:

**Synonym Filtering**:
- **Purpose**: Find all neuron types that have alternative names or synonyms from various naming conventions
- **How to Use**:
  1. Look for blue synonym tags on neuron type cards
  2. Click any synonym tag to activate the synonym filter
  3. Only neuron types with synonyms will be displayed
  4. All synonym tags across all visible cards will be highlighted in blue
  5. Click any synonym tag again to deactivate the filter
- **Use Cases**:
  - Finding neuron types with historical or alternative naming
  - Identifying types referenced in multiple studies
  - Discovering naming conventions across different datasets

**Flywire Type Filtering**:
- **Purpose**: Find neuron types that have meaningful Flywire cross-references (Flywire synonyms that differ from the neuron type name)
- **How to Use**:
  1. Look for green Flywire type tags on neuron type cards
  2. Click any Flywire type tag to activate the Flywire filter
  3. Only neuron types with displayable Flywire types will be shown
  4. All Flywire type tags across all visible cards will be highlighted in green
  5. Click any Flywire type tag again to deactivate the filter
- **Important Note**: This filter only shows neuron types where the Flywire synonym is different from the neuron type name:
  - ✅ `Tm3` with Flywire synonym `CB1031` → Will be shown (meaningful cross-reference)
  - ❌ `AOTU019` with Flywire synonym `AOTU019` → Will not be shown (not meaningful)
- **Use Cases**:
  - Finding neuron types with cross-dataset references
  - Identifying types mapped to Flywire connectome
  - Discovering meaningful alternative identifiers for comparative analysis

##### Text Search Filter

**Real-time text-based search** that searches across:
- Neuron type names
- Synonym names
- Flywire type names
- Instant filtering as you type

##### Filter Behavior

**Independence**:
- Each filter type works independently
- Multiple basic filters can be combined (ROI + neurotransmitter, etc.)
- Only one tag-based filter (synonym OR Flywire) can be active at a time

**Interaction Rules**:
- Clicking a synonym tag while a Flywire filter is active will switch to synonym filtering
- Clicking a Flywire tag while a synonym filter is active will switch to Flywire filtering
- Basic dropdown filters can be combined with tag-based filters

**Visual Feedback**:
- Active filters are clearly indicated through:
  - Highlighted tags (blue for synonyms, green for Flywire types)
  - Updated filter status messages
  - Real-time count updates of visible results

**Reset Options**:
- **Individual Reset**: Click the same tag type again to deactivate
- **Clear All**: Use the "Clear Filters" button to reset all filters
- **Filter Switch**: Click a different tag type to switch filters
- **Page Refresh**: Reloads with no active filters

##### Troubleshooting Filters

**Common Issues**:

*"No results found"*
- Check if multiple restrictive filters are applied
- Try clearing all filters and starting over
- Verify the dataset contains the expected data

*"Flywire filter shows no results"*
- This dataset may not have meaningful Flywire cross-references
- Remember that identical Flywire synonyms are not considered displayable

*"Tags not highlighting correctly"*
- Ensure JavaScript is enabled
- Check for browser console errors
- Try refreshing the page



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

**Special Features**:
- Adapted for FlyWire-specific data structures
- Handles different soma side nomenclature (CENTER vs MIDDLE)
- Optimized queries for FAFB database schema

**Important Notes**:
- **ROI Checkboxes**: Not available for FAFB datasets due to neuroglancer limitations
- **Soma Sides**: Uses "C" for center instead of "M" for middle
- **Template Selection**: Automatically uses FAFB-specific neuroglancer templates

**Why No ROI Checkboxes?**
FAFB neuroglancer data lacks reliable ROI visualization support. The system automatically detects FAFB datasets and removes ROI checkboxes to prevent user confusion. ROI statistics are still displayed for reference.

### CNS, Hemibrain, and Optic-Lobe Datasets

**Full Feature Set**:
- Complete ROI checkbox functionality for 3D visualization
- Standard soma side classifications (L, R, M)
- Full neuroglancer integration with mesh overlays
- Complete connectivity visualization

### Dataset Detection

The system automatically detects dataset type and adapts functionality:

- **FAFB Detection**: Dataset name contains "fafb" (case-insensitive)
- **Other Datasets**: Assume full ROI visualization capability
- **Automatic Adaptation**: No user configuration required

## Understanding the Interface

### ROI (Region of Interest) Features

**For CNS, Hemibrain, and Optic-Lobe Datasets**:

**Interactive ROI Table** (for CNS/Hemibrain/Optic-Lobe datasets):
- Checkbox column for toggling ROI visibility in neuroglancer
- ROI Name with innervation statistics (∑ In, % In, % Out)
- Real-time interaction with 3D viewer

**Interactive Behavior**:
1. **Click to Toggle**: Click any ROI checkbox to show/hide that region in neuroglancer
2. **Visual Feedback**: Checked boxes (☑) show active ROIs, unchecked (☐) show inactive
3. **Real-time Updates**: Neuroglancer viewer updates immediately when checkboxes change
4. **Multi-selection**: Multiple ROIs can be selected simultaneously
5. **Persistent State**: ROI selections maintained during navigation

**For FAFB Dataset**:

**View-Only ROI Table** (for FAFB datasets):
- Statistical reference without interactive checkboxes
- ROI Name with innervation data for analysis
- Clean interface without false interaction promises

**View-Only Mode**:
1. **Statistical Reference**: ROI table provides innervation data for analysis
2. **No Interactive Elements**: Checkboxes not displayed to avoid confusion
3. **Clean Interface**: Maintains professional appearance without false promises
4. **Data Accuracy**: All ROI statistics remain accurate and useful

#### ROI Data Quality and Reliability

The neuView system has been enhanced with significant improvements to ROI data quality and reliability:

**Always Up-to-Date Data**:
- ROI information is automatically fetched from the latest source datasets
- No more outdated or inconsistent ROI lists
- Data reflects the most current brain atlas information

**Improved ROI Selection Accuracy**:
- Fixed issue where brain ROI selections could incorrectly affect VNC regions
- Each ROI selection now correctly targets its intended brain region
- Enhanced layer assignment ensures proper neuroglancer visualization

**Enhanced Data Consistency**:
- ROI names and IDs are synchronized with source datasets
- Corrected naming inconsistencies (e.g., proper "WTct" vs "NTct" labels)
- Accurate ROI ordering that matches actual segment IDs

**Reliability Features**:
- Local caching ensures fast performance
- Automatic fallback to cached data if network issues occur
- Error-resistant design maintains functionality under various conditions

**What This Means for Users**:
- ✅ More reliable ROI checkbox behavior
- ✅ Accurate region highlighting in neuroglancer
- ✅ Current and consistent ROI information
- ✅ Better performance with intelligent caching
- ✅ Seamless experience even with network issues

These improvements ensure that ROI interactions work correctly and reliably across all supported datasets.

### Connectivity Tables

**Table Columns**:
- **Partner**: Neuron type that connects to/from the main neuron type
- **#**: Number of partner neurons of this type
- **NT**: Neurotransmitter (ACh, Glu, GABA, etc.)
- **Conns**: Average connections per neuron of the main type
- **CV**: Coefficient of variation for connections per neuron (measures variability)
- **%**: Percentage of total input/output connections

**Coefficient of Variation (CV)**:
- Measures how variable the connection strengths are across partner neurons
- Formula: CV = standard deviation / mean of connections per neuron
- Provides normalized measure comparable across different connection scales
- **Interpretation Guide**:
  - **CV = 0.0**: No variation (single partner neuron)
  - **Low CV (0.0-0.3)**: Consistent connection strengths across partners
  - **Medium CV (0.3-0.7)**: Moderate variation in connection strengths
  - **High CV (0.7+)**: High variation, some partners much stronger than others

**CV Usage Examples**:
- CV = 0.25 for L1 partners: Most L1 neurons have similar connection counts
- CV = 0.75 for Tm9 partners: Few strong Tm9 connections, many weak ones
- CV = 0.0 for Mi1 partners: Only one Mi1 neuron connects (no variation)

**Combined Pages (e.g., Dm4.html)**:
- Shows merged entries: "L1 - 545 connections" (combining L1(L) + L1(R))
- CV values are weighted averages: CV = Σ(cv_i × count_i) / Σ(count_i)
- Example: L1(L) CV=0.25 (20 neurons) + L1(R) CV=0.30 (8 neurons) → L1 CV=0.268
- Cleaner visualization with reduced redundancy
- Neuroglancer links include neurons from both hemispheres

**Individual Hemisphere Pages (e.g., Dm4_L.html)**:
- Automatically generated when hemisphere-specific data exists
- Shows hemisphere-specific data exactly as stored in database
- No combination or modification of original data
- Direct neuroglancer links to hemisphere-specific neurons

**CV Applications and Benefits**:

*Research Applications*:
- **Connection Pattern Analysis**: Identify partner types with consistent vs variable connectivity
- **Circuit Reliability**: Low CV indicates reliable circuit components, high CV suggests specialization
- **Developmental Studies**: Compare CV across developmental stages to study connection refinement
- **Comparative Analysis**: Use CV to compare connection reliability across different neuron types

*Data Quality Assessment*:
- **Reconstruction Quality**: Unusually high CV may indicate incomplete reconstructions
- **Biological vs Technical Variation**: Distinguish natural biological variation from technical artifacts
- **Partner Classification**: CV helps validate partner type classifications and groupings

*Practical Usage*:
- **Circuit Modeling**: Use CV to inform computational models of circuit variability
- **Experimental Design**: Target high-CV partners for detailed experimental validation
- **Literature Comparison**: Compare CV values with published electrophysiology data

### Tooltip System

Rich HTML tooltips provide additional context throughout the interface:

**Basic Tooltips**:
- Hover over "?" icons for detailed explanations
- Rich HTML content with formatted text and lists
- Automatic positioning to stay within viewport

**Usage Examples**:
- Neuroglancer explanations and usage tips
- Data field definitions and calculations
- Feature descriptions and limitations

**Mobile Support**:
- Touch-friendly sizing and positioning
- Simplified layouts for small screens
- Responsive text sizing

### Understanding the Data

**Neuron Counts**:
- Based on reconstructed neurons in the dataset
- May vary between hemispheres due to reconstruction completeness
- Combined counts represent total across both hemispheres

**Connectivity**:
- Verified synaptic connections from electron microscopy
- Connection weights represent synapse counts
- Partner percentages calculated relative to total connections

**Hemisphere Classifications**:
- Based on anatomical position of cell body (soma)
- L = Left hemisphere, R = Right hemisphere
- C/M = Center/Middle (combined or midline neurons)

**ROI Data**:
- Regions of Interest with innervation statistics
- Pre/Post counts indicate input/output synapses
- Percentages show relative innervation strength

**Neurotransmitter Predictions**:
- Computational predictions requiring experimental validation
- Confidence scores indicate prediction reliability
- Multiple predictions possible for single neuron type

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
- Verbose connection test: `pixi run neuview --verbose test-connection`

**Connection Issues**
**Advanced Connection Debugging**:
- Verbose connection testing: `pixi run neuview --verbose test-connection`
- Server configuration: Edit `neuprint.server` setting in `config.yaml`
- Network connectivity: `ping neuprint.janelia.org`

**Performance Issues**
**Performance Issue Commands**:
- Check output directory for cached files: `ls -la output/.cache/`
- Clear corrupted cache: `rm -rf output/.cache/`
- Enable performance monitoring: Use `--verbose` flag for detailed operation logs

**Missing Output**
**Missing Output Troubleshooting**:
- Verify generation: `ls -la output/`
- Regenerate with verbose output: `pixi run neuview --verbose generate -n YourNeuronType`
- Check index generation: `pixi run neuview --verbose create-list`

**ROI Checkboxes Not Working**

For CNS/Hemibrain/Optic-Lobe datasets:

Recent improvements have resolved most ROI checkbox issues:
- ✅ Fixed ROI ID collision issues (brain vs VNC regions)
- ✅ Improved layer assignment accuracy
- ✅ Enhanced data consistency and reliability

If you still experience issues:
1. **Refresh the page**: Recent fixes may require a page reload
2. **Check browser console**: Look for JavaScript errors (F12 → Console)
3. **Verify neuroglancer loads**: Ensure the 3D viewer appears properly
4. **Try different ROIs**: Test with various brain regions

**Common Solutions**:
- Clear browser cache and reload the page
- Ensure JavaScript is enabled in your browser
- Try a different supported browser (Chrome/Firefox recommended)

For FAFB datasets:
- This is expected behavior - FAFB doesn't support ROI checkboxes
- ROI data is still accurate for analysis purposes
- Use other navigation methods in neuroglancer

### Debug Mode

Enable detailed troubleshooting:

**Debug Mode Setup**: Run `pixi run neuview --verbose generate -n Dm4`

This provides:
- Detailed operation logging
- Performance timing information
- Database query details
- Cache operation tracking
- Memory usage statistics

### Getting Help

1. **Check built-in help**: `pixi run neuview --help`
2. **Test connection**: `pixi run neuview test-connection`
3. **Review configuration**: Verify your `config.yaml`
4. **Check cache**: Check `output/.cache/` directory for cached files
5. **Use verbose mode**: Add `--verbose` to any command
6. **Check logs**: Look for error messages in console output

### Browser Compatibility

**Recommended Browsers**:
- Chrome 90+ (recommended for best performance)
- Firefox 88+
- Safari 14+
- Edge 90+

**Required Features**:
- JavaScript enabled
- SVG support for visualizations
- CSS3 support for responsive design

**Mobile Support**:
- Responsive design works on tablets and phones
- Touch-friendly interface elements
- Optimized for smaller screens

## Reference

### File Organization

**Generated Output Structure**:
- **Main files**: `index.html` (navigation/search), `types.html` (filterable list), `help.html` (documentation)
- **Individual pages**: `types/` directory with hemisphere-specific pages (e.g., `Dm4.html`, `Dm4_L.html`, `Dm4_R.html`)
- **Visualizations**: `eyemaps/` directory with region-specific spatial images
- **Assets**: `static/` directory containing CSS, JavaScript, and image resources
- **System files**: `.log/` (citation tracking, rotation backups), `.cache/` (performance optimization)

### Configuration Reference

**Complete Configuration Structure** - See `config.yaml` for full examples:
- **neuprint**: Server, dataset, and token configuration
- **output**: Directory settings
- **html**: Title prefix, GitHub/YouTube links, and analytics settings (including Fathom analytics)
- **cache**: Performance caching configuration (TTL, memory limits, directories)
- **visualization**: Hexagon size, spacing, and color palette settings
- **neuroglancer**: Base URL configuration for Neuroglancer integration
- **discovery**: Auto-discovery settings (max_types, type_filter, exclude_types, include_only, randomize)

- **subsets**: Predefined sets of neuron types for validation and testing purposes

#### HTML Configuration

The `html` section controls website appearance and integrations:

```yaml
html:
  title_prefix: "Male CNS"                    # Prefix for page titles
  github_repo: "https://github.com/..."       # Optional GitHub repository link
  youtube_channel: "https://www.youtube.com/..." # Optional YouTube channel link
  fathom_id: "YOUR_FATHOM_SITE_ID"           # Optional Fathom analytics site ID
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

When viewing generated pages:

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + F` | Search within page |
| `Ctrl/Cmd + Shift + F` | Search across all tables |
| `Escape` | Clear search filters |
| `Tab` | Navigate between interactive elements |
| `Enter` | Activate focused element |

### Dataset-Specific Notes

**Hemibrain Dataset**:
- Most complete connectivity data
- Full ROI visualization support
- Standard soma side classifications
- Comprehensive neurotransmitter predictions

**CNS Dataset**:
- Focus on central nervous system
- Complete feature support
- Standard data format
- Good performance characteristics

**Optic-Lobe Dataset**:
- Specialized for visual system neurons
- Full neuroglancer integration
- Rich connectivity analysis
- Optimized eyemap visualizations

**FAFB (FlyWire) Dataset**:
- Largest dataset with ongoing updates
- Limited ROI visualization (by design)
- Special soma side handling (CENTER vs MIDDLE)
- Automated template selection

### Frequently Asked Questions

**Q: Why don't I see ROI checkboxes for my FAFB dataset?**
A: This is intentional. FAFB neuroglancer data doesn't support reliable ROI visualization, so checkboxes are hidden to prevent confusion. ROI statistics are still accurate and displayed.

**Q: How do I generate pages for all neuron types?**
A: Use `pixi run neuview fill-queue --all` to create queue entries for all neuron types, then process them with `pixi run neuview pop` repeatedly, or use the queue system for more control.

**Q: Can I customize the HTML output?**
A: Yes, you can provide custom templates by modifying the built-in template files in the templates directory.

**Q: How do I improve generation speed?**
A: Enable caching (default), use batch processing with queues, and ensure adequate memory allocation. Cache provides significant performance improvements.

**Q: What browsers are supported?**
A: Modern browsers (Chrome, Firefox, Safari, Edge) with JavaScript enabled. Chrome is recommended for optimal performance.

**Q: How do I export data from the generated pages?**
A: Use the export functions in data tables, or enable JSON export in configuration to generate machine-readable data alongside HTML.

**Q: Have there been recent improvements to ROI functionality?**
A: Yes! Recent updates include: (1) Fixed ROI ID collision issues between brain and VNC datasets, (2) Improved ROI checkbox accuracy and reliability, (3) Dynamic ROI data fetching for always up-to-date information, (4) Enhanced error handling and caching. These improvements ensure ROI selections work correctly and consistently across all datasets.

**Q: How does automatic page generation work?**
A: neuView analyzes your neuron data and automatically creates the appropriate pages:
- For neuron types with multiple hemispheres (L/R/M): Creates individual hemisphere pages AND a combined page
- For neuron types with only one hemisphere: Creates only that hemisphere's page (no combined page)
- No soma-side specification needed - the system detects and generates optimal page sets automatically

**Q: Can I still generate hemisphere-specific pages?**
A: Yes, but it's automatic! neuView will generate hemisphere-specific pages (e.g., Dm4_L.html, Dm4_R.html) whenever hemisphere-specific data exists. The system automatically detects available hemispheres and creates appropriate pages.

---

This user guide provides comprehensive coverage of neuView's features and functionality. For technical implementation details, see the [Developer Guide](developer-guide.md).
