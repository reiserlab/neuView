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
- **Data Layer**: NeuPrint API, persistent file-based caching with pickle
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

neuView uses pixi for task management with separate commands for different types of work:

#### Testing Tasks

**Unit Tests** - Fast, isolated tests for individual components:
**Unit Test Commands** (defined in `pyproject.toml`):
- `pixi run unit-test` - Run all unit tests
- `pixi run integration-test` - Run integration tests
- `pixi run test` - Run all tests

**Integration Tests** - End-to-end tests for component interactions:
**Integration Test Commands** (defined in `pyproject.toml`):
- `pixi run integration-test` - Run all integration tests
- `pixi run integration-test-verbose` - Detailed output with specific file targeting support

**General Testing**:
**Combined Test Commands** (defined in `pyproject.toml`):
- `pixi run test` - Run all tests (unit + integration)
- `pixi run test-verbose` - Detailed output for all tests
- `pixi run test-coverage` - Generate coverage reports

#### Code Quality Tasks

**Code Quality Commands** (defined in `pyproject.toml`):
- `pixi run format` - Format code with ruff

**Content Generation:**
- `pixi run neuview generate` - Generate website for 10 random neuron types
    - `pixi run neuview generate -n Dm4` - Generate website for a specific neuron type, here *Dm4*
- `pixi run neuview inspect <type>` - Inspect neuron type data
- `pixi run create-all-pages` - Generate website with all neurons in the data set. **Note:** This command will also increment the version in git.

**Content Generation Commands** (defined in `pyproject.toml`):
- `pixi run clean-output` - Clean generated output
- `pixi run fill-all` - Fill processing queue with all neuron types
- `pixi run pop-all` - Process all items in queue
- `pixi run create-list` - Generate index page
- `pixi run create-all-pages` - Complete workflow automation

## Neuron Data System

The neuron search functionality uses a dual-source data loading system that provides universal compatibility and external API access.

**Development Support Commands** (defined in `pyproject.toml`):
- `pixi run setup-env` - Setup development environment
- `pixi run help` - CLI help system
- `pixi run subset-medium` / `pixi run subset-medium-no-index` - Generate medium-sized test datasets
- `pixi run subset-small` / `pixi run subset-small-no-index` - Generate small test datasets
- `pixi run extract-and-fill` - Batch processing from config files

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

**Version Management** (defined in `pyproject.toml`):
- `pixi run increment-version` - Increment patch version and create git tag

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

### Summary Statistics Preparation

**Statistics Calculation** (`src/neuview/services/template_context_service.py`):

The TemplateContextService handles all summary statistics calculations before template rendering, keeping business logic separated from template presentation logic. This service prepares pre-calculated statistics that templates can directly use without performing complex calculations.

**Key Methods:**
- `prepare_summary_statistics` - Main entry point that routes based on soma side (left, right, middle, or combined)
- `_prepare_side_summary_stats` - Calculates statistics for individual hemisphere pages (left, right, middle)
- `_prepare_combined_summary_stats` - Calculates statistics for combined pages showing all hemispheres

**Side-Specific Statistics (left, right, middle pages):**

For individual hemisphere pages, the service calculates and provides neuron counts, synapse counts (pre and post), averages per neuron, and connection statistics specific to that hemisphere. This includes total synapses, upstream and downstream connections, and per-neuron averages for both synapses and connections.

**Combined Statistics (combined pages):**

For combined pages, the service calculates statistics across all hemispheres, including neuron counts for left, right, and middle sides, hemisphere-specific synapse totals, per-hemisphere average synapses per neuron, and overall connection statistics. This allows templates to display comparative information across hemispheres.

**Template Usage:**

All calculations are pre-computed and available via the summary_stats context variable in templates. Templates can directly reference these pre-calculated values without performing any arithmetic or conditional logic, keeping templates focused on presentation.

**Benefits:**
- Templates focus on presentation, not calculation
- All calculations are unit tested in Python code
- Better error handling for edge cases like division by zero or missing data
- Easier to maintain and modify calculation logic in one centralized location
- Consistent with other data processing services like ConnectivityCombinationService and ROICombinationService

**Adding New Calculations:**

To extend the system with new calculated statistics, add the calculation logic to either the side-specific or combined statistics method, include the new value in the returned dictionary, write a unit test to verify the calculation, and reference the new value in templates through the summary_stats context variable.

### Connectivity Table Template Processing

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

**PerformanceMonitor** (`src/neuview/services/performance_monitor.py`):
- Operation timing and metrics collection
- Key methods: `start_timer()`, `end_timer()` for performance measurement
- Metrics aggregation and reporting functionality
- Integration with logging system for performance analysis

### Cache Management Patterns

The neuView system follows consistent patterns for cache organization and management across all services.

#### Cache Directory Structure

All caches are organized under the output directory to maintain consistency. Standard structure includes roi_data, neuprint, templates, and performance subdirectories. See `src/neuview/services/` for cache organization patterns.

#### Cache Location Pattern

**Cache Location Pattern**: Services derive cache locations from container-provided output directory. Implementation pattern demonstrated in `ROIDataService.__init__()` and other service constructors.

**Benefits**:
- ✅ Consistent cache organization across all services
- ✅ Configurable output directory support
- ✅ No hardcoded cache paths
- ✅ Clean separation by service type

#### Cache Key Strategy

**Cache Key Strategy**: Use descriptive, collision-resistant cache keys incorporating dataset, type, and version information. Examples: "fullbrain_roi_v4.json", "vnc_neuropil_roi_v0.json". Implementation in `ROIDataService._get_cache_filename()`.

#### Cache Lifecycle Management

**Cache Lifecycle Management**: Implement cache validation and refresh mechanisms with time-based expiration. See `ROIDataService._is_cache_valid()` and `_fetch_and_parse_roi_data()` for reference implementation patterns.

#### Error-Resilient Caching

**Error-Resilient Caching**: Implement graceful fallback to stale cache on network failures. Reference implementation in `ROIDataService._fetch_and_parse_roi_data()` demonstrates try-catch patterns with fallback logic.

#### Container Integration Pattern

**Container Integration Pattern**: Register cache-aware services with output directory injection. See `roi_data_service_factory()` in `PageGenerationContainer` for reference implementation.



## Development Patterns

### Error Handling

**Error Handling Pattern** (`src/neuview/services/` - various service implementations):
- Consistent use of Result pattern for error handling
- Comprehensive exception catching with specific error types
- Reference implementation in `PageGenerationOrchestrator.generate_page()`
- Key pattern: validate input → fetch data → process → return Result
- Logging integration for debugging and monitoring

### Configuration Management

**Configuration Management** (`src/neuview/config/config.py`):
- Hierarchical configuration system with dataclass structure
- Key config classes: `Config`, `NeuPrintConfig`, `CacheConfig`, `OutputConfig`, `HtmlConfig`
- Class methods: `from_file()` for YAML loading, `from_env()` for environment variables
- Configuration validation with `__post_init__()` methods

### Service Registration

**Service Registration** (`src/neuview/services/page_generation_container.py`):
- Dependency injection setup through `PageGenerationContainer`
- Factory functions for service creation with proper dependency resolution
- Key services registered: cache_service, database_service, connectivity_service, template_service
- Service lifecycle management and singleton patterns
- Reference implementation in container `__init__()` method

### Type Safety

Using type hints and validation:
**Type Safety** (`src/neuview/domain/` and service modules):
- Comprehensive use of dataclasses and type hints throughout codebase
- Domain models with strict typing in `src/neuview/domain/`
- Example classes: `AnalysisRequest`, `NeuronType`, `ConnectivityData`
- Function signatures with explicit return types using `Result` pattern

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

**Test execution tasks are defined in `pyproject.toml`:**
- Unit tests: `pixi run unit-test` (fast feedback)
- Integration tests: `pixi run integration-test` (comprehensive testing)
- All tests: `pixi run test` (complete test suite)
- Coverage reports: `pixi run test-coverage`
- Verbose output: Add `--verbose` suffix to any test command

# Run only integration tests
pixi run integration-test

# Run with coverage
pixi run test-coverage

# Run specific test file
pixi run pytest test/unit/test_neuron_type.py
```

### Test Structure

**Test Organization** (`test/` directory):
- `test_dataset_adapters.py` - Unit tests for factory and adapters
- `test_male_cns_integration.py` - Integration tests for end-to-end scenarios
- `services/` - Service-specific test modules
- `visualization/` - Visualization component tests

### Naming Conventions

- **Unit tests**: Focus on single method/function behavior
  - Format: `test_[specific_behavior]`
  - Example: `test_male_cns_base_name_alias_resolution`

- **Integration tests**: Focus on component interactions
  - Format: `test_[workflow_or_integration_scenario]`
  - Example: `test_end_to_end_male_cns_workflow`

### Performance Guidelines

- **Unit tests**: Should complete in under 1 second total
- **Integration tests**: May take several seconds due to file I/O and component setup
- **Full test suite**: Typically < 10 seconds

### CI/CD Integration

**CI/CD Integration** (`.github/workflows/` directory):
- Separate GitHub Actions jobs for unit and integration tests
- Unit tests provide fast feedback with `pixi run unit-test-verbose`
- Integration tests use secure token injection for NeuPrint access
- Parallel execution for efficient CI pipeline

### Adding New Tests

When adding new features:

1. **Add unit tests** for individual components
2. **Add integration tests** if the feature involves multiple components
3. **Use appropriate markers** (`@pytest.mark.unit` or `@pytest.mark.integration`)
4. **Follow naming conventions**
5. **Ensure proper cleanup** of resources in integration tests

### Test Fixtures

neuView uses inline pytest fixtures defined within individual test files rather than a centralized factory pattern.

**Fixture Pattern** (defined in test files):
- Unit tests: Use `@pytest.fixture` with `unittest.mock.Mock` objects
- Integration tests: Use temporary config files and real database connections
- Test-specific fixtures: Defined inline for clarity and simplicity

**Example Fixture** (`test/services/test_neuron_selection_service.py`):
```python
@pytest.fixture
def selection_service():
    """Create NeuronSelectionService instance."""
    mock_config = Mock()
    return NeuronSelectionService(mock_config)

@pytest.fixture
def mock_connector():
    """Create mock connector for testing."""
    connector = Mock()
    connector.dataset_adapter = Mock()
    connector.dataset_adapter.dataset_info = Mock()
    return connector
```

**Example Mock Data** (`test/services/test_soma_detection_service.py`):
```python
@pytest.fixture
def mock_query_result_bilateral():
    """Mock DataFrame result for bilateral neuron type."""
    mock_result = MagicMock()
    mock_result.empty = False
    mock_result.iloc = [
        {"leftCount": 10, "rightCount": 8, "middleCount": 0, "totalCount": 18}
    ]
    return mock_result
```

**Test Data Strategies:**
- **Unit tests**: Use `unittest.mock.Mock` and `MagicMock` for fast, isolated testing
- **Integration tests**: Connect to real NeuPrint database or use temporary config files
- **Config objects**: Use `Config.create_minimal_for_testing()` for test configurations

**Benefits:**
- Simple and maintainable (no central dependency)
- Test data visible next to tests that use it
- Easy to modify fixtures for specific test needs
- Minimal boilerplate and coupling between test files

### Script Management

The neuView project follows specific patterns for managing utility scripts in the `scripts/` directory.

#### Script Categories

**Permanent Scripts** (Keep):
- Regular maintenance utilities
- Reusable development tools
- System health checks
- Data migration tools for ongoing use
- Performance monitoring scripts

**Temporary Scripts** (Remove after use):
- One-time migration scripts
- Debugging scripts for specific issues
- Verification scripts for completed work
- Testing scripts for specific features

#### Script Lifecycle Management

**Script Classification Examples**:
- **Permanent**: `scripts/increment_version.py` - Reusable version management functionality
- **Temporary**: Issue-specific debugging scripts - Should be removed after resolution

See current utility scripts in `scripts/` directory for reference implementations.

#### Cleanup Best Practices

1. **Mark Temporary Scripts**: Use clear naming and documentation
2. **Clean After Completion**: Remove debugging scripts once issues are resolved
3. **Document Purpose**: Include clear descriptions of script intent
4. **Regular Cleanup**: Periodically review and remove obsolete scripts

#### Script Documentation Pattern

**Documentation Requirements**: All permanent scripts should include comprehensive docstrings with purpose, usage, and requirements. See `scripts/increment_version.py` and `scripts/extract_and_fill.py` for reference documentation patterns.



#### Current Utility Scripts

**Version Management**:
**Current Utility Scripts** (see `scripts/` directory):
- `increment_version.py`: Automatically increments project version and creates git tags (supports `--dry-run`)
- `extract_and_fill.py`: Extracts neuron types from config files and runs fill-queue commands

**Usage**: See script docstrings and `scripts/README.md` for detailed usage instructions and examples.

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

### Environment Variables

Environment variable support for sensitive configuration:

#### Currently Implemented

- `NEUPRINT_TOKEN` - NeuPrint API token (required)
  - Checked in three locations: `.env` file, environment, config.yaml

### Configuration Validation

**Configuration Validation** (`src/neuview/config/config.py`):
- Automatic validation with clear error messages using dataclass `__post_init__()` methods
- Example: `NeuPrintConfig.__post_init__()` validates required server and dataset fields
- Validation occurs at configuration loading time with descriptive error messages

## API Reference

### Core Classes

#### PageGenerator

**PageGenerator** (`src/neuview/page_generator.py`):
- Main interface for page generation with configuration and service container integration
- Key methods: `generate_page()`, `generate_index()`, `test_connection()`
- Handles automatic soma-side detection and page creation orchestration

#### NeuronType

**NeuronType** (`src/neuview/domain/neuron_type.py`):
- Core domain entity with properties: name, description, custom_query
- Represents neuron type metadata and configuration

#### Result Pattern

**Result Pattern** (`src/neuview/domain/result.py`):
- Explicit error handling pattern used throughout the codebase
- Static methods: `success()`, `failure()` for result creation
- Properties: `is_success()`, `value`, `error` for result handling
- Ensures predictable error handling across all services

### Service Interfaces

#### DatabaseQueryService

**DatabaseQueryService** (`src/neuview/services/database_query_service.py`):
- Database query execution with parameter binding
- Key method: `execute_query()` returns Result pattern for error handling
- Handles NeuPrint API interactions and query optimization

#### CacheService

**CacheService** (`src/neuview/services/cache_service.py`):
- Multi-level caching with memory, file, and database backends
- Key methods: `get()`, `set()` with optional TTL support
- Automatic cache eviction and persistence management

#### CitationService

**CitationService** (`src/neuview/services/citation_service.py`):
- Citation management and HTML link generation from CSV data
- Key methods: `load_citations()`, `get_citation()`, `create_citation_link()`
- Automatic missing citation logging and validation
- Supports custom link text and output directory configuration

## CLI Reference

### Overview

neuView provides a comprehensive command-line interface for generating neuron type pages, managing the processing queue, and testing connections. All commands support the `--verbose` flag for detailed logging output.

### Global Options

Available for all commands:

- `-c, --config TEXT` - Path to configuration file (default: `config.yaml`)
- `-v, --verbose` - Enable verbose output and DEBUG level logging
- `--version` - Show neuView version from git tags and exit
- `--help` - Show help message and exit

### Commands

#### generate

Generate HTML pages for neuron types.

**Usage:**
```bash
neuview generate [OPTIONS]
```

**Options:**
- `--neuron-type, -n TEXT` - Specific neuron type to generate page for
- `--output-dir TEXT` - Custom output directory (overrides config)
- `--image-format [svg|png]` - Format for hexagon grid images (default: svg)
- `--embed/--no-embed` - Embed images directly in HTML instead of saving to files (default: no-embed)
- `--minify/--no-minify` - Enable/disable HTML minification (default: minify)

**Examples:**
```bash
# Generate page for specific neuron type
neuview generate --neuron-type Tm3

# Generate with PNG images and embedded content
neuview generate -n Dm4 --image-format png --embed

# Generate without minification for debugging
neuview generate -n SAD103 --no-minify

# Auto-discover and generate for multiple types (up to 20)
neuview generate
```

#### inspect

Inspect detailed information about a specific neuron type including counts, soma sides, and synapse statistics.

**Usage:**
```bash
neuview inspect NEURON_TYPE
```

**Arguments:**
- `NEURON_TYPE` - Name of the neuron type to inspect (required)

**Examples:**
```bash
# Get detailed statistics for Tm3
neuview inspect Tm3

# Inspect with verbose logging
neuview --verbose inspect Dm4
```

**Output includes:**
- Total neuron count
- Soma side distribution (left/right/middle)
- Bilateral ratio
- Synapse statistics (average, median, std dev)
- Computation timestamp

#### test-connection

Test connection to the NeuPrint server and verify dataset access.

**Usage:**
```bash
neuview test-connection [OPTIONS]
```

**Options:**
- `--detailed` - Show detailed dataset information
- `--timeout INTEGER` - Connection timeout in seconds (default: 30)

**Examples:**
```bash
# Basic connection test
neuview test-connection

# Detailed server and dataset information
neuview test-connection --detailed

# With custom timeout
neuview test-connection --timeout 60
```

#### fill-queue

Create YAML queue files with generate command options and update JSON cache manifest. This is the first step in batch processing workflows.

**Usage:**
```bash
neuview fill-queue [OPTIONS]
```

**Options:**
- `--neuron-type, -n TEXT` - Specific neuron type to add to queue
- `--all` - Create queue files for all discovered neuron types and update cache manifest
- `--output-dir TEXT` - Custom output directory
- `--image-format [svg|png]` - Format for hexagon grid images (default: svg)
- `--embed/--no-embed` - Embed images directly in HTML (default: no-embed)

**Examples:**
```bash
# Add single neuron type to queue
neuview fill-queue --neuron-type Tm3

# Fill queue with all discovered types
neuview fill-queue --all

# Fill queue with custom options
neuview fill-queue --all --image-format png --embed
```

**Queue Files:**
- Created in `output/.queue/` directory
- YAML format with command parameters
- Includes `.lock` mechanism to prevent concurrent processing
- Updates `output/.cache/cache_manifest.json`

#### pop

Pop and process a single queue file from the processing queue. Processes one item at a time using FIFO order.

**Usage:**
```bash
neuview pop [OPTIONS]
```

**Options:**
- `--output-dir TEXT` - Custom output directory
- `--minify/--no-minify` - Enable/disable HTML minification (default: minify)

**Examples:**
```bash
# Process one queue item
neuview pop

# Process without minification
neuview pop --no-minify

# Process all items in queue (using pixi task)
pixi run pop-all
```

**Processing:**
- Acquires file lock to prevent concurrent processing
- Reads YAML queue file
- Generates page with stored parameters
- Removes queue file on success
- Returns lock file to `.yaml` on error for retry

#### create-list

Generate an index page listing all available neuron types with ROI analysis and comprehensive neuron information.

**Usage:**
```bash
neuview create-list [OPTIONS]
```

**Options:**
- `--output-dir TEXT` - Output directory to scan for neuron pages
- `--minify/--no-minify` - Enable/disable HTML minification (default: minify)

**Examples:**
```bash
# Create index page
neuview create-list

# Create without minification
neuview create-list --no-minify
```

**Generated Files:**
- `output/index.html` - Main index page
- Uses cached neuron type data to avoid database re-queries
- Includes ROI analysis across all neuron types
- Provides search and filter functionality

### Verbose Logging

The `--verbose` flag enables DEBUG level logging throughout the application. This provides detailed information about:

- Cache operations (hits, misses, saves, expirations)
- Database query execution and results
- File operations and path resolutions
- Data processing steps and transformations
- ROI hierarchy loading and validation
- Template rendering and context preparation
- Performance timing for operations

**Example with verbose output:**
```bash
neuview --verbose generate --neuron-type Tm3
```

**Logger output includes:**
- Timestamp for each operation
- Logger name (module path)
- Log level (DEBUG, INFO, WARNING, ERROR)
- Detailed message with context

**Key loggers to watch:**
- `neuview.cache` - Cache operations and expiration
- `neuview.services.*` - Service-level operations
- `neuview.visualization.*` - Data processing and visualization

## Cache Implementation Details

### Overview

neuView uses a persistent file-based caching system with pickle serialization to store expensive query results and computed data across sessions.

### Cache Architecture

**Implementation:** `src/neuview/strategies/cache/file_cache.py`

The cache system provides:
- **Persistent storage** - Data survives application restarts
- **TTL support** - Automatic expiration of stale data
- **Thread-safe operations** - Concurrent access protection with `threading.RLock()`
- **Metadata tracking** - Separate files for expiration information
- **MD5 key hashing** - Safe filename generation from cache keys

### Cache Types

#### File Cache Strategy

**Primary cache backend** using pickle serialization:

```python
class FileCacheStrategy(CacheStrategy):
    def __init__(self, cache_dir: str, default_ttl: Optional[int] = None)
```

**Features:**
- Stores data in `{cache_dir}/{md5_hash}.cache` files
- Metadata stored in `{md5_hash}.meta` files
- Automatic directory creation
- Configurable TTL (default: 24 hours for neuron type cache)
- Thread-safe read/write operations

#### Memory Cache Strategy

**Fast in-memory cache** for frequently accessed data:

```python
class MemoryCacheStrategy(CacheStrategy):
```

**Features:**
- LRU eviction policy
- No persistence across restarts
- Fastest access times
- Used for temporary computation results

#### Composite Cache

**Multi-level caching** combining memory and file strategies:

```python
class CompositeCacheStrategy(CacheStrategy):
```

**Behavior:**
- Checks memory cache first (fastest)
- Falls back to file cache on miss
- Promotes file cache hits to memory
- Writes to all configured levels

### Cache Directory Structure

```
output/
├── .cache/
│   ├── {md5_hash}.cache          # Pickled data
│   ├── {md5_hash}.meta           # TTL metadata (JSON)
│   ├── roi_hierarchy.json        # ROI hierarchy cache
│   └── cache_manifest.json       # Neuron type manifest
└── .queue/
    ├── {neuron_type}.yaml        # Queue files
    └── {neuron_type}.yaml.lock   # Processing locks
```

### Cache Key Strategy

**Key generation:**
```python
safe_key = hashlib.md5(key.encode()).hexdigest()
```

**Key components typically include:**
- Neuron type name
- Query parameters
- Dataset identifier
- Soma side filter
- ROI context

**Example keys:**
- `neuron_type:Tm3:soma_side:left`
- `roi_hierarchy:male-cns:v0.9`
- `connectivity:Tm3:threshold:5`

### Cache Lifecycle Management

#### Saving Data

```python
cache_manager.save_neuron_type_cache(cache_data)
```

**Process:**
1. Serialize data to JSON (for neuron type cache) or pickle (for general cache)
2. Generate MD5 hash from cache key
3. Write data to `{hash}.cache` file
4. Write metadata with TTL to `{hash}.meta` file
5. Log operation at DEBUG level

#### Loading Data

```python
cache_data = cache_manager.load_neuron_type_cache(neuron_type)
```

**Process:**
1. Generate cache key and hash
2. Check if cache file exists
3. Load metadata and check expiration
4. Return `None` if expired
5. Deserialize and return data if valid
6. Log cache hit/miss at DEBUG level

#### Invalidation

```python
cache_manager.invalidate_neuron_type_cache(neuron_type)
```

**Strategies:**
- Manual: `rm -rf output/.cache/`
- Programmatic: `cache_manager.invalidate_neuron_type_cache()`
- Automatic: TTL expiration (default: 24 hours)

### Error-Resilient Caching

**All cache operations use try/except:**
- Cache failures never block page generation
- Warnings logged for debugging
- Graceful degradation to database queries
- Missing cache treated as cache miss

**Example pattern:**
```python
try:
    # Attempt cache operation
    cache_data = load_from_cache(key)
except Exception as e:
    logger.warning(f"Cache operation failed: {e}")
    cache_data = None  # Proceed without cache
```

### Cache Performance

**Expected behavior:**
- First generation: Cache miss, query database (~2-5s per type)
- Subsequent generations: Cache hit, no database query (~50-200ms)
- Index generation: Uses cached data, no re-queries
- Cache expiry: 24 hours default (configurable)

**Cache hit rates:**
- Development: ~30-50% (frequent invalidation)
- Production: ~90-95% (stable data)
- Index generation: ~100% (relies on generation cache)

### Container Integration Pattern

**Service container provides cache service:**

```python
@property
def cache_service(self) -> NeuronTypeCacheManager:
    if not self._cache_service:
        cache_dir = self.config.output.directory / ".cache"
        self._cache_service = NeuronTypeCacheManager(cache_dir=str(cache_dir))
    return self._cache_service
```

**Benefits:**
- Single cache instance per container
- Lazy initialization
- Consistent cache location
- Easy dependency injection

## Queue System Details

### Overview

The queue system enables batch processing of neuron types with parallel execution support, avoiding duplicate work and providing fault tolerance.

### Queue Architecture

**Implementation:** `src/neuview/services/queue_file_manager.py`, `src/neuview/services/queue_processor.py`

### Queue File Format

Queue files are YAML documents storing generation parameters:

```yaml
neuron_type: "Tm3"
output_directory: "output"
image_format: "svg"
embed_images: false
minify: true
config_file: "config.yaml"
```

### Queue Directory Structure

```
output/.queue/
├── Tm3.yaml                    # Ready to process
├── Dm4.yaml.lock              # Currently processing
├── SAD103.yaml                # Waiting
└── AOTU019.yaml               # Waiting
```

### Lock File Mechanism

**Purpose:** Prevent concurrent processing of the same neuron type

**Process:**
1. `pop` command finds first `.yaml` file
2. Renames to `.yaml.lock` (atomic operation)
3. Processes the queue item
4. Deletes `.lock` file on success
5. Renames back to `.yaml` on error for retry

**Benefits:**
- Atomic lock acquisition
- No orphaned locks (file-based)
- Simple error recovery
- Visible processing state

### Queue Operations

#### Fill Queue

**Single neuron type:**
```bash
neuview fill-queue --neuron-type Tm3
```

**All discovered types:**
```bash
neuview fill-queue --all
```

**Custom parameters:**
```bash
neuview fill-queue --all --image-format png --embed
```

#### Process Queue

**Single item (manual):**
```bash
neuview pop
```

**All items (parallel with pixi):**
```bash
pixi run pop-all
```

This uses GNU Parallel to process multiple items concurrently:
```bash
yes pop | head -n $(find output/.queue -name '*.yaml' | wc -l) | parallel --no-notice neuview
```

#### Queue Status

**Check queue size:**
```bash
ls -1 output/.queue/*.yaml | wc -l
```

**List pending items:**
```bash
ls -1 output/.queue/*.yaml
```

**Check for locked items:**
```bash
ls -1 output/.queue/*.lock
```

#### Clear Queue

**Remove all queue files:**
```bash
rm -rf output/.queue/
```

**Remove specific neuron type:**
```bash
rm output/.queue/Tm3.yaml*
```

### Cache Manifest Integration

**File:** `output/.cache/cache_manifest.json`

**Purpose:** Track all neuron types in the queue for index generation

**Structure:**
```json
{
  "neuron_types": ["Tm3", "Dm4", "SAD103"],
  "last_updated": "2024-01-15T10:30:00",
  "total_count": 3
}
```

**Updates:**
- `fill-queue --all` creates/updates manifest
- `create-list` uses manifest to discover available types
- Avoids database queries during index generation

### Workflow Integration

**Complete batch workflow:**
```bash
# 1. Clean previous output
pixi run clean-output

# 2. Fill queue with all types
pixi run fill-all

# 3. Process all items in parallel
pixi run pop-all

# 4. Generate index page
pixi run create-list

# 5. Increment version
pixi run increment-version
```

**Or use the combined task:**
```bash
pixi run create-all-pages
```

### Error Handling

**Queue processing errors:**
- Lock file renamed back to `.yaml`
- Error message logged
- Item remains in queue for retry
- No data corruption

**Common errors:**
- Database connection timeout → Retry queue item
- Invalid neuron type → Remove from queue manually
- Missing dependencies → Check environment setup
- Permission errors → Check output directory permissions

### Performance Considerations

**Serial processing:**
- ~2-5 seconds per neuron type (with cache misses)
- ~50-200ms per neuron type (with cache hits)
- Predictable, sequential

**Parallel processing:**
- Use `pixi run pop-all` (GNU Parallel)
- Processes multiple items concurrently
- Limited by database connection pool
- 3-5x faster for large queues

## Dataset Aliases

### Overview

neuView supports dataset aliases to handle different naming conventions for the same underlying dataset type. This is particularly useful when working with datasets that may have different names but use the same database structure and query patterns.

### Current Aliases

#### CNS Dataset Aliases
The following aliases are configured to use the CNS adapter:

- `male-cns` → `cns`
- `male-cns:v0.9` → `cns` (versioned)

### Implementation

**DatasetAdapterFactory** (`src/neuview/services/dataset_adapters/dataset_adapter_factory.py`):
- Handles dataset alias resolution and adapter creation
- Maintains adapter registry and alias mappings
- Key method: `create_adapter()` with versioned dataset name support
- Aliases: `male-cns` → `cns` with version handling
        base_name = dataset_name.split(":")[0] if ":" in dataset_name else dataset_name

- Alias resolution and adapter creation logic
- Automatic fallback to CNSAdapter for unknown datasets
- Version string handling for dataset names

### Configuration Example

**Configuration Usage** (see `config.yaml` for examples):
- Dataset names support aliases: `male-cns:v0.9` resolves to CNS adapter
- Server configuration points to appropriate NeuPrint instance
- Automatic adapter selection based on dataset name patterns

This configuration will:
- Resolve `male-cns:v0.9` → `male-cns` (base name) → `cns` (alias resolution)
- Create a `CNSAdapter` instance
- Set `dataset_info.name` to `"cns"`
- **Not produce any warnings**

### Adding New Aliases

**Adding New Aliases**: Modify the `_aliases` dictionary in `DatasetAdapterFactory` class (`src/neuview/services/dataset_adapters/dataset_adapter_factory.py`). Example aliases: `male-cns` → `cns`, `female-cns` → `cns`.

### Versioned Datasets

Dataset aliases work with versioned dataset names:
- `male-cns:v0.9` → `cns`
- `male-cns` → `cns`
- `female-cns` → `cns`

### Error Handling

If a dataset name (including aliases) is not recognized:
1. Prints a warning message
2. Falls back to using the `CNSAdapter` as the default
3. Continues execution

Example warning: "Warning: Unknown dataset 'unknown-dataset:latest', using CNS adapter as default"

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

#### FAFB Query Modifications

**FAFB Query Patterns** (`src/neuview/services/database_query_service.py`):
- Database queries use CASE statements for property fallback handling
- Cypher queries account for `somaSide` vs `side` property differences
- Automatic value mapping within query logic for consistent results
- Reference implementation in FAFB-specific query methods

#### FAFB ROI Checkbox Behavior

FAFB datasets don't support ROI visualization in Neuroglancer, requiring conditional UI:

**Implementation**: Dataset-aware JavaScript that disables ROI checkboxes for FAFB:

**FAFB ROI Checkbox Behavior** (`templates/static/js/neuroglancer-url-generator.js.jinja`):
- Dataset detection: `IS_FAFB_DATASET` variable for conditional behavior
- `syncRoiCheckboxes()` function skips checkbox creation for FAFB datasets
- Automatic width adjustment for FAFB ROI cells to maintain layout consistency
- Prevents user confusion by hiding non-functional checkboxes

#### Connectivity Checkbox Self-Reference Detection

Automatic checkbox disabling when partner type matches current neuron type and bodyId is already visible in neuroglancer:

**Problem**: Users could add the same neuron instance multiple times to the neuroglancer viewer by selecting connectivity partners that reference the current neuron itself.

**Solution**: Detect self-reference conditions and disable checkboxes automatically.

**Implementation**:

1. **HTML Template Changes** (`templates/sections/connectivity.html.jinja`):
**Connectivity Template Data** (`templates/sections/connectivity_table.html.jinja`):
- Template data attributes: `data-body-ids` for JavaScript access
- Jinja2 filters: `get_partner_body_ids()` for body ID extraction
- Partner type information embedded for self-reference detection

2. **JavaScript Data** (`templates/sections/neuron_page_scripts.html.jinja`):
**JavaScript Data Integration** (`templates/sections/neuron_page_scripts.html.jinja`):
- `neuroglancerData.currentNeuronType` populated from template context
- Enables self-reference detection in connectivity checkbox logic

3. **Checkbox Logic** (`templates/static/js/neuroglancer-url-generator.js.jinja`):
**Self-Reference Detection Logic** (JavaScript in connectivity templates):
- Compares partner type with current neuron type
- Checks if body IDs are in visible neurons list
- Automatic checkbox disabling with `self-reference` CSS class application
- Prevents circular selections in Neuroglancer interface

4. **CSS Styling** (`static/css/neuron-page.css`):
**Self-Reference Styling** (`static/css/neuron-page.css`):
- `.p-c.self-reference input[type="checkbox"]` styling for disabled self-reference checkboxes
- Visual indicators: gray background, disabled cursor, reduced opacity

**Logic Flow**:
**Decision Logic Flow**:
1. Empty bodyIds → Disable (existing behavior)
2. Partner type matches current type → Check visibility
3. Body IDs in visible neurons → Disable as self-reference
4. Otherwise → Enable normally

**Example**: For neuron type AN02A005 with visible neurons [123456, 789012]:
- LC10 partner with [111111, 222222] → Enabled ✅
- AN02A005 partner with [123456] → Disabled ❌ (self-reference)
- T4 partner with [333333, 444444] → Enabled ✅

**Testing**:
- Manual: Use `test_checkbox/test_checkbox_disable.html` for demonstration
- Integration: Generate pages for self-connecting neuron types (e.g., AN02A005)
- Console: Check for debug messages like `[CHECKBOX] Disabling checkbox for self-reference`

**Performance**: O(n×m) complexity where n = partners, m = visible neurons. Minimal impact due to small datasets.

**Browser Support**: Standard JavaScript (IE11+) using `dataset` API, `Array.includes()`, and CSS `:disabled`.

**Troubleshooting**:
1. **Checkbox not disabling**: Verify `currentNeuronType` in pageData
2. **Styling issues**: Confirm `.self-reference` CSS class is applied and styles are loaded
3. **Console errors**: Check neuroglancer data initialization and function load order

#### FAFB Neuroglancer Template Selection

Automatic template selection based on dataset:

**Template Selection** (`src/neuview/services/neuroglancer_js_service.py`):
- `get_neuroglancer_template()` method selects dataset-appropriate templates
- FAFB datasets use specialized `neuroglancer-fafb.js.jinja` template
- Other datasets use standard `neuroglancer.js.jinja` template

### Dataset Detection Patterns

Centralized dataset type detection:

**Dataset Detection Patterns** (`src/neuview/services/dataset_type_detector.py`):
- Static methods for dataset type detection: `is_fafb()`, `is_cns()`, `is_hemibrain()`
- String pattern matching for dataset categorization
- Used throughout system for conditional dataset-specific behavior

## Feature Implementation Guides

### Connectivity Combination Implementation

For combined pages (automatically generated when multiple hemispheres exist), connectivity entries are automatically merged:

#### Problem
Combined pages showed separate entries:
- `L1 (R)` - 300 connections
- `L1 (L)` - 245 connections

#### Solution
`ConnectivityCombinationService` merges these into:
- `L1` - 545 connections (combined)

#### Implementation

**ConnectivityCombinationService** (`src/neuview/services/connectivity_combination_service.py`):
- Combines L/R partners for the same neuron types automatically
- Key methods: `combine_connectivity_partners()`, `_combine_partners()`
- Groups partners by base type and combines statistics (weight, connection_count)
- Handles body ID aggregation and neurotransmitter selection logic
- Automatic soma side label removal for combined view presentation

### ROI Combination Implementation

Similar to connectivity, ROI entries are automatically combined for multi-hemisphere pages:

#### Problem
Combined pages showed separate ROI entries:
- `ME_L` - 2500 pre, 1800 post synapses
- `ME_R` - 2000 pre, 1200 post synapses

#### Solution
`ROICombinationService` merges these into:
- `ME` - 4500 pre, 3000 post synapses (combined)

#### Implementation

**ROICombinationService** (`src/neuview/services/roi_combination_service.py`):
- Combines L/R ROI entries for multi-hemisphere pages automatically
- Supports multiple ROI naming patterns: `ME_L/ME_R`, `ME(L)/ME(R)`, layered patterns
- Key methods: `combine_roi_data()`, `_combine_roi_entries()`
- Aggregates synaptic statistics: pre, post, downstream, upstream counts
- Pattern matching for flexible ROI name detection and grouping

### Dynamic ROI Data System

The Dynamic ROI Data System fetches live ROI data from Google Cloud Storage, ensuring ROI information is always up-to-date.

#### Architecture

The system uses a `ROIDataService` that:

1. **Fetches Live Data**: Retrieves ROI segment properties from GCS endpoints
2. **Caches Locally**: Stores data in `output/.cache/roi_data/` for performance
3. **Template Integration**: Automatically injects ROI data as Jinja globals
4. **Error Resilience**: Falls back to cached data if network requests fail

#### ROIDataService Implementation

```python
class ROIDataService:
    """Service for fetching and caching ROI data from Google Cloud Storage."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("output")
        self.cache_dir = self.output_dir / ".cache" / "roi_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_fullbrain_roi_data(self) -> Tuple[List[int], List[str]]:
        """Fetch fullbrain ROI segment IDs and names."""
        url = "gs://flyem-male-cns/rois/fullbrain-roi-v4/segment_properties/info"
        data = self._fetch_and_parse_roi_data(url, "fullbrain_roi_v4.json")
        return data.get("ids", []), data.get("names", [])

    def get_vnc_roi_data(self) -> Tuple[List[int], List[str]]:
        """Fetch VNC ROI segment IDs and names."""
        url = "gs://flyem-male-cns/rois/malecns-vnc-neuropil-roi-v0/segment_properties/info"
        data = self._fetch_and_parse_roi_data(url, "vnc_neuropil_roi_v0.json")
        return data.get("ids", []), data.get("names", [])
```

#### Data Sources and Format

**Fullbrain ROIs**:
- **Endpoint**: `gs://flyem-male-cns/rois/fullbrain-roi-v4/segment_properties/info`
- **Count**: 90 ROIs
- **Template Variables**: `roi_ids`, `all_rois`

**VNC ROIs**:
- **Endpoint**: `gs://flyem-male-cns/rois/malecns-vnc-neuropil-roi-v0/segment_properties/info`
- **Count**: 24 ROIs
- **Template Variables**: `vnc_ids`, `vnc_names`

The GCS endpoints return Neuroglancer segment properties format:

```json
{
  "@type": "neuroglancer_segment_properties",
  "inline": {
    "ids": ["1", "2", "3", ...],
    "properties": [{
      "id": "source",
      "type": "label",
      "values": ["AL(L)", "AL(R)", "AME(L)", ...]
    }]
  }
}
```

#### Template Integration

The service integrates seamlessly with the Jinja2 template system:

```javascript
// Dynamic template variables (automatically populated)
const ROI_IDS = {{ roi_ids|tojson }};
const ALL_ROIS = {{ all_rois|tojson }};
const VNC_IDS = {{ vnc_ids|tojson }};
const VNC_NAMES = {{ vnc_names|tojson }};
```

#### Caching Strategy

- **Cache Location**: `output/.cache/roi_data/` (follows project cache patterns)
- **Cache Duration**: 1 hour (configurable)
- **Fallback Behavior**: Uses stale cache if network requests fail
- **Cache Files**:
  - `fullbrain_roi_v4.json`
  - `vnc_neuropil_roi_v0.json`

#### Container Integration

The service is automatically registered in the dependency injection container:

```python
def roi_data_service_factory(container: ServiceContainer) -> ROIDataService:
    """Factory for ROI data service with container integration."""
    config = container.get("config")
    output_dir = Path(config.output.directory) if config.output.directory else None
    return ROIDataService(output_dir=output_dir)
```

ROI data is automatically added as template globals during environment configuration:

```python
# ROI data automatically available in all templates
roi_data = self.roi_data_service.get_all_roi_data()
for key, value in roi_data.items():
    self.env.globals[key] = value
```

#### ROI ID Collision Handling

The system handles ROI ID collisions between brain and VNC datasets.

ROI segment IDs can overlap between datasets:
- ID 7: "AOTU(L)" in brain dataset, "LegNp(T2)(L)" in VNC dataset
- Without context tracking, clicking brain ROI checkboxes could toggle VNC layers

**Implementation**: The system uses context tracking with `selectedRoiContexts` map:

```javascript
// Context-aware ROI management
const selectedRoiContexts = new Map(); // Tracks 'brain' or 'vnc' context

function addBrainRoiIds(roiIds) {
    roiIds.forEach(id => selectedRoiContexts.set(id, 'brain'));
    updateNeuroglancerLayers();
}

function addVncRoiIds(roiIds) {
    roiIds.forEach(id => selectedRoiContexts.set(id, 'vnc'));
    updateNeuroglancerLayers();
}

function updateNeuroglancerLayers() {
    const brainRoiIds = [];
    const vncRoiIds = [];

    selectedRoiContexts.forEach((context, roiId) => {
        if (context === 'brain') {
            brainRoiIds.push(roiId);
        } else if (context === 'vnc') {
            vncRoiIds.push(roiId);
        }
    });

    // Assign to correct layers based on context
    setBrainNeuropilsLayer(brainRoiIds);
    setVncNeuropilsLayer(vncRoiIds);
}
```

This ensures ROI selections are always assigned to the correct Neuroglancer layer regardless of ID overlap.

#### Benefits

✅ **Always Current**: ROI data reflects latest source changes automatically
✅ **Zero Maintenance**: Eliminates manual hardcoded array updates
✅ **Data Integrity**: Single source of truth prevents inconsistencies
✅ **Performance**: Local caching minimizes network overhead
✅ **Reliability**: Graceful fallback handling for network issues
✅ **Correct Behavior**: ROI ID collision resolution ensures proper layer assignment

#### Testing and Validation

Comprehensive test coverage ensures system reliability:

- **Service Tests**: Validate GCS connectivity and data parsing
- **Template Integration Tests**: Verify Jinja2 rendering with ROI data
- **Cache Tests**: Confirm caching behavior and fallback mechanisms
- **Collision Tests**: Verify correct layer assignment for overlapping IDs

### Coefficient of Variation (CV) Implementation

The CV feature adds variability analysis to connectivity tables, showing how consistent connection strengths are within each partner type.

#### Problem
Connectivity tables only showed average connection counts but provided no insight into the variability of connections across individual partner neurons.

#### Solution
Added coefficient of variation calculation and display:
- CV = standard deviation / mean of connections per neuron
- Values range from 0 (no variation) to higher values (more variation)
- Provides normalized measure comparable across different scales

#### Data Collection Implementation

Modified `neuprint_connector.py` to track individual partner neuron weights:

```python
# In connectivity query processing
type_soma_data[key] = {
    "type": record["partner_type"],
    "soma_side": soma_side,
    "total_weight": 0,
    "connection_count": 0,
    "neurotransmitters": {},
    "partner_body_ids": set(),
    "partner_weights": {},  # NEW: Track weights per partner neuron
}

# Track weights per partner neuron for CV calculation
partner_id = record["partner_bodyId"]
if partner_id not in type_soma_data[key]["partner_weights"]:
    type_soma_data[key]["partner_weights"][partner_id] = 0
type_soma_data[key]["partner_weights"][partner_id] += int(record["weight"])

### Synonym and Flywire Type Filtering Implementation

The Types page includes specialized filtering functionality for synonym and Flywire type tags that allows users to filter neuron types based on additional naming information.

#### Problem
Users needed a way to quickly identify neuron types that have:
1. Synonyms (alternative names from various naming conventions)
2. Flywire types that are different from the neuron type name (meaningful cross-references)

The challenge was ensuring that clicking on Flywire tags only shows cards with displayable Flywire types (different from the neuron name), not just any Flywire synonym.

#### Solution
Implemented independent filtering for synonym and Flywire type tags with proper handling of displayable vs. non-displayable Flywire types.

#### Template Data Structure

The template receives processed data with separate attributes:

**Template Data Structure** (`templates/index.html.jinja`):
- Data attributes embedded in neuron card wrappers for JavaScript access
- Key attributes: `data-synonyms`, `data-processed-synonyms`, `data-flywire-types`, `data-processed-flywire-types`
- Raw vs processed data separation for filtering logic
- Template processing handles empty values and type differences

#### JavaScript Filter Implementation

Independent filter variables track each filter type:

**JavaScript Filter Implementation** (`templates/static/js/filtering.js`):
- Independent filter variables for each filter type: `currentSynonymFilter`, `currentFlywireTypeFilter`
- Separate click handlers for synonym-tag and flywire-type-tag elements
- Toggle behavior between "all" and specific filter states
- State management prevents filter conflicts

#### Filter Logic Implementation

**Synonym Filter:**
**Filter Logic Implementation** (`templates/static/js/filtering.js`):
- **Synonym Filter**: `matchesSynonym()` checks both raw synonyms and processed synonyms data
- **Flywire Filter**: `matchesFlywireType()` uses only processed flywire types for displayable differences
- Closure pattern for encapsulated filter logic with data attribute access
- Handles empty data gracefully with fallback to empty strings

#### Visual Feedback Implementation

Independent highlighting for each filter type:

**Visual Feedback Implementation** (`templates/static/js/filtering.js`):
- Dynamic CSS class management for filter tag highlighting
- `selected` class application based on current filter state
- Separate handling for synonym-tag and flywire-type-tag elements
- jQuery-based DOM manipulation for visual state updates

#### Key Implementation Details

1. **Displayable Flywire Types**: The critical distinction is that `processedFlywireTypes` contains only Flywire synonyms that differ from the neuron type name. For example:
   - AOTU019 with Flywire synonym "AOTU019" → Not in `processedFlywireTypes`
   - Tm3 with Flywire synonym "CB1031" → Included in `processedFlywireTypes`

2. **Independent Filtering**: Each filter type works independently - only one can be active at a time.

3. **Filter Reset**: Clicking a tag of a different type automatically resets the other filter and switches to the new one.

4. **CSS Integration**: Uses existing CSS classes `.synonym-tag.selected` and `.flywire-type-tag.selected` for visual feedback.

#### Data Flow

1. **Backend Processing**: Creates `processed_synonyms` and `processed_flywire_types` with only displayable items
2. **Template Rendering**: Outputs data attributes for both raw and processed data
3. **JavaScript Filtering**: Uses appropriate data attribute based on filter type
4. **Visual Feedback**: Highlights all tags of the active filter type

This implementation ensures perfect alignment between what users see (displayed tags) and what the filter shows (matching cards).

#### CSS Integration

The filtering system uses existing CSS classes for visual feedback:

**CSS Integration** (`static/css/neuron-page.css`):
- Tag styling for synonym-tag and flywire-type-tag elements
- Selected state styling with color inversions and shadow effects
- Cursor pointer for interactive elements
- Color schemes: blue for synonyms, green for flywire types

#### Performance Considerations

1. **DOM Queries**: Filters cache jQuery selections to avoid repeated DOM queries
2. **Event Delegation**: Uses delegated event handlers for dynamic content
3. **Debouncing**: Text search includes debouncing to prevent excessive filtering
4. **Data Attributes**: Uses data attributes for efficient filtering logic

#### Testing Strategy

The filtering implementation can be tested with:

**Testing Strategy** (JavaScript console testing):
- State management assertions for initial filter states
- Filter logic validation with test card data
- Visual feedback verification through DOM element counting
- Console logging for debugging filter behavior

#### CV Calculation

**CV Implementation** (`src/neuview/services/partner_analysis_service.py`):
- Coefficient of variation calculation for connections per neuron
- Statistical analysis: variance, standard deviation, and CV computation
- Handles edge cases: single partner neurons (CV = 0), division by zero
- Integration with partner data structure for upstream/downstream analysis

#### CV Combination for L/R Entries

**CV Combination Logic** (`src/neuview/services/connectivity_combination_service.py`):
- Enhanced `_merge_partner_group()` method with CV field support
- Weighted average calculation for combined CV values
- Partner neuron count weighting for statistical accuracy
- Proper handling of missing CV data and edge cases

#### Template Integration

**Template CV Integration** (`templates/sections/connectivity_table.html.jinja`):
- CV column headers with descriptive tooltips
- Safe template rendering with `partner.get('coefficient_of_variation', 0)` pattern
- Consistent upstream and downstream table structure
- Fallback value handling for missing CV data

#### CV Interpretation

| CV Range | Interpretation | Biological Meaning |
|----------|---------------|-------------------|
| 0.0 | No variation | Single partner neuron |
| 0.0 - 0.3 | Low variation | Consistent connection strengths |
| 0.3 - 0.7 | Medium variation | Moderate variability |
| 0.7+ | High variation | Some partners much stronger |

#### Testing Implementation

**CV Testing** (`test/test_cv_implementation.py`):
- `test_cv_calculation()` - Tests CV computation with various scenarios (high/low variation)
- `test_cv_combination()` - Validates weighted average calculation for L/R entry combinations
- Comprehensive test cases covering edge cases and statistical accuracy
- Assertion-based validation for CV calculation correctness

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
pixi run neuview --verbose generate
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

#### Citation Logging

neuView includes dedicated citation logging for tracking missing citations:

```python
# Citation logging is automatically configured
# Log files are created in output/.log/missing_citations.log

# View citation issues
cat output/.log/missing_citations.log

# Monitor in real-time
tail -f output/.log/missing_citations.log

Citation logging is automatically enabled when an output directory is provided to text processing utilities. See the `TextUtils.process_synonyms` method and related text processing functions for automatic citation logging integration.

**Citation Log Features**:
- Rotating log files (1MB max, keeps 5 backups)
- Timestamped entries with context information
- UTF-8 encoding for international characters
- Dedicated logger (`neuview.missing_citations`)
- No interference with other system logs

#### Development Mode

Enable development mode by running neuview with the `--verbose` flag:

```bash
neuview --verbose generate --neuron-type Tm3
```

This enables DEBUG level logging which provides:
- Detailed cache operation logging (hits, misses, saves, expirations)
- ROI hierarchy loading and validation details
- File operation and path resolution tracking
- Data processing steps and transformations
- Performance timing information for some operations
- Citation tracking and missing citation warnings



### Logging Architecture

neuView uses Python's standard `logging` module with a multi-logger architecture for different concerns.

#### System Loggers

The system uses separate loggers throughout the codebase:

**Primary loggers:**
- `neuview.cache` - Cache operations (NeuronTypeCacheManager)
- `neuview.services.*` - Service-level operations
- `neuview.visualization.*` - Data processing and visualization
- `neuview.missing_citations` - Dedicated citation tracking

**Logger configuration:**
- Default level: WARNING (set in `cli.py`)
- Verbose mode: DEBUG (enabled with `--verbose` flag)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Key modules with active logging:**
- `src/neuview/cache.py` - 13 logger calls for cache operations
- `src/neuview/visualization/` - Multiple logger calls for data processing
- `src/neuview/services/citation_service.py` - Citation tracking

#### Citation Logging Implementation

The citation logging system uses a dedicated logger with rotating file handlers:

**Implementation details:**
- **Logger name:** `neuview.missing_citations`
- **Handler:** `RotatingFileHandler` (1MB max size, 5 backups)
- **Level:** INFO (independent of main logger level)
- **Format:** Timestamped entries with context
- **Encoding:** UTF-8 for international character support

**Setup location:** `src/neuview/services/citation_service.py` in `_setup_citation_logger()` method

**Automatic triggers:**
- Text processing with synonyms (`TextUtils.process_synonyms()`)
- Citation link creation (`CitationService.create_citation_link()`)
- Missing citation references in templates

#### Integration Points

Citation logging is integrated into:

1. **TextUtils.process_synonyms()**: Logs missing citations during synonym processing
2. **CitationService.create_citation_link()**: Logs missing citations during link creation
3. **Template rendering**: Automatic context passing for logging

#### Log File Management

- **Location**: `output/.log/missing_citations.log`
- **Rotation**: Automatic when file reaches 1MB
- **Backups**: Up to 5 backup files kept
- **Format**: Timestamped with context information
- **Encoding**: UTF-8 for international support

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
