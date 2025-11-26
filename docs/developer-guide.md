# neuView Developer Guide

A comprehensive guide for developers working on the neuView neuron visualization platform.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Neuron Data System](#neuron-data-system)
- [Core Components](#core-components)
- [Service Architecture](#service-architecture)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Template System](#template-system)
- [Performance & Caching](#performance--caching)
- [Testing Strategy](#testing-strategy)
- [Configuration](#configuration)
- [Dataset-Specific Implementations](#dataset-specific-implementations)
- [Troubleshooting](#troubleshooting)

## Project Overview

neuView is a modern Python CLI tool that generates beautiful HTML pages for neuron types using data from NeuPrint. Built with Domain-Driven Design (DDD) architecture for maintainability and extensibility.

### Key Features

- **🔌 NeuPrint Integration**: Direct data fetching with intelligent caching
- **📱 Modern Web Interface**: Responsive design with advanced filtering and search
- **⚡ High Performance**: Persistent caching with optimal data loading strategies
- **🧠 Multi-Dataset Support**: Automatic adaptation for CNS, Hemibrain, Optic-lobe, FAFB
- **🎨 Beautiful Reports**: Clean, accessible HTML pages with interactive features
- **🔍 Advanced Search**: Real-time autocomplete search with synonym and FlyWire type support

### Technology Stack

- **Backend**: Python 3.11+, asyncio for async processing
- **Data Layer**: NeuPrint API, persistent caching with SQLite
- **Frontend**: Modern HTML5, CSS3, vanilla JavaScript
- **Templates**: Jinja2 with custom filters and extensions
- **Testing**: pytest with comprehensive coverage
- **Package Management**: pixi for reproducible environments

### Architecture Overview

neuView follows a layered architecture pattern:

- **Presentation Layer**: CLI Commands, Templates, Static Assets, HTML Generation
- **Application Layer**: Services, Orchestrators, Command Handlers, Factories
- **Domain Layer**: Entities, Value Objects, Domain Services, Business Logic
- **Infrastructure Layer**: Database, File System, External APIs, Caching, Adapters

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pixi package manager
- NeuPrint access token
- Git for version control

### Development Setup

1. **Clone the repository**
2. **Install dependencies**: `pixi install`
3. **Set up environment**: `pixi run setup-env` and edit `.env` with your NeuPrint token
4. **Verify setup**: `pixi run neuview test-connection`

### Development Commands

**Testing:**
- `pixi run unit-test` - Run all unit tests
- `pixi run integration-test` - Run integration tests
- `pixi run test` - Run all tests

**Code Quality:**
- `pixi run lint` - Run ruff linter
- `pixi run format` - Format code with ruff

**Content Generation:**
- `pixi run neuview build` - Generate website
- `pixi run neuview inspect <type>` - Inspect neuron type data

## Neuron Data System

The neuron search functionality uses a dual-source data loading system that provides universal compatibility and external API access.

### Architecture

```
output/
├── data/
│   ├── neurons.json          # Primary: JSON for external services & HTTP(S)
│   └── neurons.js            # Fallback: JavaScript wrapper for file:// access
└── static/
    └── js/
        └── neuron-search.js  # Search logic (no embedded data)
```

### Data Format (Version 2.0)

**Structure:**
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
  ],
  "metadata": {
    "generated": "2025-01-26 15:04:31",
    "total_types": 28,
    "version": "2.0"
  }
}
```

**Key Points:**
- URLs stored WITHOUT `types/` prefix (added dynamically in JavaScript)
- `types.flywire` and `types.synonyms` are arrays
- `types` field only included when it has content
- Same structure for both `neurons.json` and `neurons.js`

### Data Loading Flow

**Web Server (HTTP/HTTPS):**
1. neuron-search.js loads
2. Attempts `fetch('data/neurons.json')`
3. Success → Uses JSON data (optimal)
4. neurons.js never downloaded

**Local Files (file://):**
1. neuron-search.js loads
2. Attempts `fetch('data/neurons.json')`
3. Fails (CORS restriction)
4. Dynamically loads `<script src="data/neurons.js">`
5. Script tag bypasses CORS → Success

### CORS Bypass Mechanism

- `fetch()` requests are subject to CORS policy (blocked on file://)
- `<script>` tags are NOT subject to CORS (works on file://)
- Dynamic script injection used as fallback

### Search Functionality

The search system searches in three places:
1. **Neuron names** (e.g., "AN07B013")
2. **Synonyms** (e.g., "Cachero 2010: aSP-j")
3. **FlyWire types** (e.g., "CB3127")

**Synonym Matching:**
- Full text match: "cachero" matches "Cachero 2010: aSP-j"
- Name after colon: "asp-j" matches "aSP-j" part

### External API Access

**Python Example:**
```python
import requests

data = requests.get('https://site.com/data/neurons.json').json()
neuron_names = data['names']
neurons = data['neurons']

for neuron in neurons:
    if 'types' in neuron:
        flywire = neuron['types'].get('flywire', [])
        synonyms = neuron['types'].get('synonyms', [])
```

**JavaScript Example:**
```javascript
const response = await fetch('https://site.com/data/neurons.json');
const data = await response.json();

const names = data.names;
const neurons = data.neurons;
```

**cURL Example:**
```bash
curl -s https://site.com/data/neurons.json | jq '.names'
curl -s https://site.com/data/neurons.json | jq '.neurons[] | select(.types.flywire[]? == "CB3127")'
```

### Generation Process

Data files are generated automatically during build by `IndexGeneratorService.generate_neuron_search_js()`:

1. Prepares neuron data structure from NeuPrint data
2. Strips `types/` prefix from URLs
3. Converts `flywire_types` string to `types.flywire` array
4. Converts `synonyms` string to `types.synonyms` array
5. Generates `output/data/neurons.json`
6. Generates `output/data/neurons.js`
7. Generates `output/static/js/neuron-search.js`

**File:** `src/neuview/services/index_generator_service.py`

### URL Handling

**In Data (JSON/JS):**
- URLs stored without `types/` prefix
- Example: `"combined": "AN07B013.html"`

**In JavaScript:**
```javascript
// Prefix added dynamically based on context
this.urlPrefix = this.isNeuronPage ? '' : 'types/';
targetUrl = this.urlPrefix + neuronEntry.urls.combined;

// From index.html: 'types/AN07B013.html'
// From neuron page: 'AN07B013.html'
```

### Testing

**Test page:** `docs/neuron-data-test.html`
- Tests JSON loading
- Tests JS fallback loading
- Shows data statistics
- Provides debugging tools

**Verify data source in browser console:**
```javascript
console.log(window.neuronSearch.dataSource);
// Returns: 'json' or 'js-fallback'
```

## Core Components

### PageGenerator

Main class responsible for generating HTML pages. Coordinates template rendering, data fetching, and file writing.

**Location:** `src/neuview/core/page_generator.py`

### PageGenerationOrchestrator

Orchestrates the entire page generation process, managing parallelization and error handling.

**Location:** `src/neuview/application/orchestrators/page_generation_orchestrator.py`

### NeuronType Class

Domain model representing a neuron type with all its properties and behaviors.

**Location:** `src/neuview/domain/entities/neuron_type.py`

## Service Architecture

### Core Services

**Data Services:**
- `DatabaseQueryService` - NeuPrint queries
- `ConnectivityQueryService` - Connectivity data
- `ROIDataService` - Brain region data

**Analysis Services:**
- `StatisticsService` - Statistical calculations
- `CVCalculatorService` - Coefficient of variation

**Content Services:**
- `CitationService` - Citation generation
- `ImageService` - Image handling
- `IndexGeneratorService` - Index page and data file generation

**Infrastructure Services:**
- `CacheService` - Data caching
- `ConfigurationService` - Configuration management

### Service Container Pattern

Services are registered in a dependency injection container for loose coupling.

**Location:** `src/neuview/infrastructure/container.py`

## Data Processing Pipeline

### Dataset Adapters

Different datasets (CNS, Hemibrain, FAFB) require different handling. Adapters normalize the differences.

**Base Adapter:** `src/neuview/infrastructure/adapters/base_adapter.py`

**Implementations:**
- `CNSAdapter` - For CNS datasets
- `FafbAdapter` - For FAFB/FlyWire datasets

### Data Flow

1. **Query** - Fetch data from NeuPrint
2. **Adapt** - Normalize dataset-specific differences
3. **Process** - Calculate statistics, generate visualizations
4. **Cache** - Store processed data
5. **Render** - Generate HTML with templates
6. **Write** - Output to file system

### Connectivity Data Processing with CV

Connectivity tables include coefficient of variation (CV) to show variability in synapse counts.

**Formula:** `CV = (standard deviation / mean) × 100`

**Implementation:** `src/neuview/services/cv_calculator_service.py`

## Template System

### Template Architecture

Templates are organized hierarchically with inheritance and includes.

**Base Templates:**
- `base.html.jinja` - Main page structure
- `macros.html.jinja` - Reusable components

**Page Templates:**
- `neuron_page.html.jinja` - Individual neuron pages
- `index.html.jinja` - Landing page
- `types.html.jinja` - Neuron type listing
- `help.html.jinja` - Help page

**Partial Templates:**
- `sections/header.html.jinja` - Page header with search
- `sections/footer.html.jinja` - Page footer
- `sections/connectivity_table.html.jinja` - Connectivity tables

### Template Context

Templates receive context dictionaries with data:

```python
context = {
    'neuron': neuron_type,
    'config': configuration,
    'statistics': stats,
    'connectivity': conn_data,
    'citations': citations
}
```

### Custom Template Filters

**Location:** `src/neuview/templates/filters/`

Custom Jinja2 filters for formatting data in templates.

## Performance & Caching

### Multi-Level Cache System

1. **Memory Cache** - In-process cache for current session
2. **Persistent Cache** - SQLite database for cross-session caching
3. **File Cache** - Generated HTML and static assets

### Cache Types

- **Query Cache** - NeuPrint query results
- **Synapse Cache** - Connectivity statistics
- **ROI Cache** - Brain region data
- **Image Cache** - Neuroglancer screenshots

### Performance Optimizations

- Parallel page generation with asyncio
- Lazy loading of heavy data
- Incremental regeneration (only changed pages)
- Efficient template rendering

### Cache Management

**Clear cache:**
```bash
pixi run neuview build --clear-cache
```

**Cache location:**
- Default: `.neuview_cache/`
- Configurable via environment variable

## Testing Strategy

### Test Categories

**Unit Tests** (`@pytest.mark.unit`):
- Fast, isolated tests
- No external dependencies
- Mock all services

**Integration Tests** (`@pytest.mark.integration`):
- Test component interactions
- May use real NeuPrint connection
- Slower but more comprehensive

### Test Execution

```bash
# Run all tests
pixi run test

# Run only unit tests
pixi run unit-test

# Run only integration tests
pixi run integration-test

# Run specific test file
pixi run pytest test/unit/test_neuron_type.py

# Run with coverage
pixi run pytest --cov=src
```

### Test Structure

```
test/
├── unit/              # Unit tests
│   ├── domain/
│   ├── services/
│   └── utils/
├── integration/       # Integration tests
│   ├── test_full_pipeline.py
│   └── test_neuprint_integration.py
└── fixtures/          # Test data and fixtures
```

## Configuration

### Configuration Files

**Main Config:** `config.yaml`
```yaml
neuprint:
  server: neuprint.janelia.org
  dataset: optic-lobe:v1.0
  
html:
  title_prefix: "Optic Lobe"
  github_repo: "https://github.com/..."
  
performance:
  max_workers: 4
  cache_enabled: true
```

**Environment Variables:**
- `NEUPRINT_APPLICATION_CREDENTIALS` - NeuPrint token (required)
- `NEUVIEW_CACHE_DIR` - Cache directory location
- `NEUVIEW_LOG_LEVEL` - Logging verbosity

### Configuration Validation

Configuration is validated at startup with clear error messages for issues.

## Dataset-Specific Implementations

### FAFB Dataset Handling

FAFB (FlyWire) has different property names and behaviors:

**Soma Side Property:**
- Other datasets: `somaLocation` or `somaSide`
- FAFB: `side` (values: "L", "R", "M")

**Adapter:** `src/neuview/infrastructure/adapters/fafb_adapter.py`

### CNS, Hemibrain, and Optic-Lobe Datasets

Standard property names:
- `somaLocation` or `somaSide`
- ROI information from `roiInfo` property

**Adapter:** `src/neuview/infrastructure/adapters/cns_adapter.py`

### Dataset Detection

Automatic detection based on dataset name in configuration.

## Troubleshooting

### Common Issues

**"No neuron types found"**
- Check NeuPrint credentials
- Verify dataset name in config.yaml
- Check network connectivity

**"Template rendering failed"**
- Check template syntax
- Verify all required context variables
- Look for missing filters or macros

**"Cache issues"**
- Clear cache with `--clear-cache` flag
- Check cache directory permissions
- Verify disk space

**Search not working:**
- Check browser console for errors
- Verify neurons.json and neurons.js were generated
- Check data source: `window.neuronSearch.dataSource`

### Debug Mode

Enable verbose logging:
```bash
pixi run neuview build --verbose
```

Or set environment variable:
```bash
export NEUVIEW_LOG_LEVEL=DEBUG
```

### Performance Issues

**Slow generation:**
- Enable caching
- Use `--parallel` flag
- Reduce `max_types` in discovery config

**Large output size:**
- Minimize HTML (default in production)
- Compress images
- Limit number of neuron types

### Citation Issues

**Missing citations:**
- Verify citation format in source data
- Check CitationService logs
- Ensure proper DOI formatting

**Duplicate citations:**
- Use citation deduplication
- Check citation key generation

## File Organization

```
neuview/
├── config.yaml              # Main configuration
├── src/neuview/
│   ├── core/               # Core components
│   ├── domain/             # Domain models
│   ├── application/        # Application services
│   ├── infrastructure/     # Infrastructure layer
│   ├── services/           # Business services
│   └── templates/          # Jinja2 templates
├── output/                 # Generated website
│   ├── data/
│   │   ├── neurons.json   # Neuron data (JSON)
│   │   └── neurons.js     # Neuron data (JS fallback)
│   ├── static/
│   │   ├── js/
│   │   │   └── neuron-search.js
│   │   ├── css/
│   │   └── icons/
│   ├── types/             # Individual neuron pages
│   ├── index.html         # Landing page
│   ├── types.html         # Type listing
│   └── help.html          # Help page
├── test/                   # Tests
├── docs/                   # Documentation
└── .neuview_cache/        # Cache directory
```

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Make changes with tests
3. Run tests: `pixi run test`
4. Format code: `pixi run format`
5. Lint code: `pixi run lint`
6. Submit pull request

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Keep functions focused and small
- Prefer composition over inheritance

### Testing Requirements

- Unit tests for new functions
- Integration tests for new features
- Maintain or improve coverage
- All tests must pass

### Documentation

- Update user guide for user-facing changes
- Update developer guide for architecture changes
- Add inline comments for complex logic
- Update configuration examples

## Additional Resources

- **GitHub Repository**: Project source code and issues
- **NeuPrint Documentation**: https://neuprint.janelia.org/
- **Jinja2 Documentation**: https://jinja.palletsprojects.com/
- **pytest Documentation**: https://docs.pytest.org/