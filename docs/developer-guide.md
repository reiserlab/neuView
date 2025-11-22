# neuView Developer Guide

A comprehensive guide for developers working on the neuView neuron visualization platform. This guide covers architecture, development setup, implementation details, and contribution guidelines.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Core Components](#core-components)
- [Service Architecture](#service-architecture)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Visualization System](#visualization-system)
- [Template System](#template-system)
- [Performance & Caching](#performance--caching)
- [Development Patterns](#development-patterns)
- [Testing Strategy](#testing-strategy)
- [Dataset Aliases](#dataset-aliases)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Dataset-Specific Implementations](#dataset-specific-implementations)
- [Feature Implementation Guides](#feature-implementation-guides)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Project Overview

neuView is a modern Python CLI tool that generates beautiful HTML pages for neuron types using data from NeuPrint. Built with Domain-Driven Design (DDD) architecture for maintainability and extensibility.

### Key Features

- **🔌 NeuPrint Integration**: Direct data fetching with intelligent caching
- **📱 Modern Web Interface**: Responsive design with advanced filtering
- **⚡ High Performance**: Up to 97.9% speed improvement with persistent caching
- **🧠 Multi-Dataset Support**: Automatic adaptation for CNS, Hemibrain, Optic-lobe, FAFB
- **🎨 Beautiful Reports**: Clean, accessible HTML pages with interactive features
- **🔍 Advanced Search**: Real-time filtering by cell count, neurotransmitter, brain regions

### Technology Stack

- **Backend**: Python 3.11+, asyncio for async processing
- **Data Layer**: NeuPrint API, persistent caching with SQLite
- **Frontend**: Modern HTML5, CSS3, vanilla JavaScript
- **Templates**: Jinja2 with custom filters and extensions
- **Testing**: pytest with comprehensive coverage
- **Package Management**: pixi for reproducible environments

### Architecture Overview

neuView follows a layered architecture pattern with four distinct layers:

- **Presentation Layer**: CLI Commands, Templates, Static Assets, HTML Generation
- **Application Layer**: Services, Orchestrators, Command Handlers, Factories
- **Domain Layer**: Entities, Value Objects, Domain Services, Business Logic
- **Infrastructure Layer**: Database, File System, External APIs, Caching, Adapters

For detailed architecture implementation, see `src/neuview/` directory structure.

### Key Architectural Principles

- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Single Responsibility**: Each component has one well-defined purpose
- **Open/Closed Principle**: Open for extension, closed for modification
- **Command/Query Separation**: Clear distinction between data modification and retrieval
- **Result Pattern**: Explicit error handling with Result<T> types
- **Service Container**: Dependency injection for loose coupling

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pixi package manager
- NeuPrint access token
- Git for version control

### Development Setup

1. **Clone the repository:**
Clone the repository and navigate to the project directory.

2. **Install dependencies:**
Install dependencies using `pixi install`.

3. **Set up environment:**
Set up the environment using `pixi run setup-env` and edit the .env file with your NeuPrint token.

4. **Verify setup:**
Test the connection using `pixi run neuview test-connection`.

### Development Commands

neuView uses pixi for task management with separate commands for different types of work:

#### Testing Tasks

**Unit Tests** - Fast, isolated tests for individual components:
**Unit Test Commands** (defined in `pixi.toml`):
- `pixi run unit-test` - Run all unit tests
- `pixi run unit-test-verbose` - Detailed output with specific file/test targeting support

**Integration Tests** - End-to-end tests for component interactions:
**Integration Test Commands** (defined in `pixi.toml`):
- `pixi run integration-test` - Run all integration tests
- `pixi run integration-test-verbose` - Detailed output with specific file targeting support

**General Testing**:
**Combined Test Commands** (defined in `pixi.toml`):
- `pixi run test` - Run all tests (unit + integration)
- `pixi run test-verbose` - Detailed output for all tests
- `pixi run test-coverage` - Generate coverage reports

#### Code Quality Tasks

**Code Quality Commands** (defined in `pixi.toml`):
- `pixi run format` - Format code with ruff
- `pixi run check` - Run linting and quality checks

#### Content Generation Tasks

**Content Generation Commands** (defined in `pixi.toml`):
- `pixi run clean-output` - Clean generated output
- `pixi run fill-all` - Fill processing queue with all neuron types
- `pixi run pop-all` - Process all items in queue
- `pixi run create-list` - Generate index page
- `pixi run create-all-pages` - Complete workflow automation

Queue management implemented in `src/neuview/services/queue_service.py`.

#### Development Support Tasks

**Development Support Commands** (defined in `pixi.toml`):
- `pixi run setup-env` - Setup development environment
- `pixi run help` - CLI help system
- `pixi run subset-medium` / `pixi run subset-medium-no-index` - Generate medium-sized test datasets
- `pixi run subset-small` / `pixi run subset-small-no-index` - Generate small test datasets
- `pixi run extract-and-fill` - Batch processing from config files

Implementation in `scripts/extract_and_fill.py` and CLI modules.

#### Version Management Tasks

The project includes automated version management for releases:

**Version Management** (defined in `pixi.toml`):
- `pixi run increment-version` - Increment patch version and create git tag

Implementation in `scripts/increment_version.py` with `--dry-run` support for testing.

**Version Increment Script**

The `increment_version.py` script automatically manages project versioning by:

1. **Reading current version**: Uses `git tag --list --sort=-version:refname` to find the latest semantic version tag
2. **Incrementing patch version**: Increases patch by 1 (e.g., `v2.7.1` → `v2.7.2`)
3. **Creating git tag**: Creates an annotated tag with descriptive message

**Version Format**

- Expects/creates semantic versioning: `v{major}.{minor}.{patch}`
- The `v` prefix is optional when reading, always added when creating
- Handles missing patch numbers by defaulting to 0

**Safety Features**

- Validates version format before processing
- Warns about uncommitted changes but continues
- Checks for duplicate tags to prevent conflicts
- Does not auto-push tags (manual `git push origin <tag>` required)
- Supports `--dry-run` mode for testing

**Example Output**

The version increment process analyzes the current version, calculates the new version, creates a git tag, and reports the successful increment.

**Error Handling**

The script will exit with error code 1 if:
- No valid semantic version tags are found
- Git commands fail
- Tag already exists
- Version format is invalid

#### Task Usage Patterns

**Development Workflow**:
1. Setup environment: `pixi run setup-env` (first time)
2. Development testing: `pixi run unit-test-verbose`
3. Code quality: `pixi run format` and `pixi run check`
4. Pre-commit testing: `pixi run test-verbose`

**Content Generation Workflow**:
- Complete automation: `pixi run create-all-pages`
- Manual steps: clean → fill → process → index

**Testing Workflow**:
- Development: `pixi run unit-test` for fast feedback
- Release preparation: `pixi run integration-test` and `pixi run test-coverage`

#### Performance Notes

- **Unit tests**: Complete in ~1 second
- **Integration tests**: May take several seconds due to I/O
- **Full test suite**: Typically < 10 seconds
- **Page generation**: Varies based on dataset size

#### Environment Requirements

Most development tasks require the `dev` environment, which is automatically used by the configured tasks. Some tasks require authentication:
- Set in `.env` file or environment variables

## Core Components

### PageGenerator

The main orchestrator that coordinates page generation across all services.

**PageGenerator** (`src/neuview/page_generator.py`):
- Core page generation orchestration
- Automatic soma side detection and page creation
- Service container integration
- Key methods: `generate_page()`, `generate_index()`, `test_connection()`

### PageGenerationOrchestrator

Coordinates the complex page generation workflow through a multi-step process including request validation, data fetching, connectivity processing, visualization generation, template rendering, and output saving.

**PageGenerationOrchestrator** (`src/neuview/services/page_generation_orchestrator.py`):
- Coordinates the complete page generation workflow
- Handles request validation, data fetching, processing, and rendering
- Manages service dependencies and error handling

### NeuronType Class

Core domain entity representing a neuron type with methods for cache key generation, neuron counting, and synapse statistics.

**NeuronType** (`src/neuview/domain/neuron_type.py`):
- Domain entity representing a neuron type
- Properties: name, description, custom_query
- Methods: `get_cache_key()`, `get_neuron_count()`, `get_synapse_stats()`

## Service Architecture

### Core Services

The application is built around a comprehensive service architecture:

#### Data Services
- **NeuPrintConnector**: Database connection and query execution
- **DatabaseQueryService**: Structured query building and execution
- **CacheService**: Multi-level caching with persistence
- **DataProcessingService**: Data transformation and validation
- **ROIDataService**: Dynamic ROI data fetching from Google Cloud Storage with caching

#### Analysis Services
- **PartnerAnalysisService**: Connectivity analysis and partner identification
- **ROIAnalysisService**: Region of interest analysis and statistics
- **ConnectivityCombinationService**: Automatic L/R hemisphere combination for connectivity
- **ROICombinationService**: Automatic L/R hemisphere combination for ROI data

#### Content Services
- **TemplateContextService**: Template data preparation and processing
- **ResourceManagerService**: Static asset management
- **NeuroglancerJSService**: Neuroglancer integration and URL generation
- **URLGenerationService**: Dynamic URL creation
- **CitationService**: Citation data management and HTML link generation
- **CitationLoggingService**: Automatic tracking and logging of missing citations

#### Infrastructure Services
- **FileService**: File operations and path management
- **ConfigurationService**: Configuration loading and validation
- **LoggingService**: Structured logging and monitoring

### Service Container Pattern

Dependency injection using a service container with service registration and singleton management.

See the `ServiceContainer` class in `src/neuview/services/page_generation_container.py` for the complete implementation including the `__init__`, `register`, and `get` methods.

### Service Development Pattern

Standard pattern for implementing new services with configuration injection, caching integration, error handling, input validation, and core processing logic.

Refer to any service class in `src/neuview/services/` for examples of this pattern, such as `DatabaseQueryService` in `src/neuview/services/database_query_service.py` or `CacheService` in `src/neuview/services/cache_service.py`.

## Data Processing Pipeline

### Dataset Adapters

Different datasets require different data processing approaches:

**Dataset Adapters** (`src/neuview/services/dataset_adapters/`):
- Base adapter pattern for dataset-specific processing
- `DatasetAdapter` - Abstract base class with common interface
- `CNSAdapter`, `HemibrainAdapter`, `FAFBAdapter` - Dataset-specific implementations
- Key methods: `extract_soma_side()`, `normalize_columns()`, `categorize_rois()`
- Factory pattern in `DatasetAdapterFactory` for automatic adapter selection

### Data Flow

Raw NeuPrint Data → Dataset Adapter → Cache Layer → Service Processing → Template Rendering

1. **Data Extraction**: NeuPrint queries return raw database results
2. **Adaptation**: Dataset-specific adapters normalize the data
3. **Caching**: Processed data is cached for performance
4. **Analysis**: Services perform connectivity and ROI analysis with CV calculation
5. **Rendering**: Template system generates final HTML

### Connectivity Data Processing with CV

The connectivity processing pipeline includes statistical analysis including coefficient of variation (CV) calculation. See the connectivity query methods and CV calculation logic in `src/neuview/services/data_processing_service.py` and `src/neuview/services/connectivity_combination_service.py`.

The partner data structure includes the calculated CV value for template rendering.

### Automatic Page Generation System

neuView features automatic page generation that eliminates the need for manual soma-side specification. The system intelligently analyzes neuron data and generates the optimal set of pages.

#### Architecture Overview

The automatic page generation system analyzes soma side distribution, determines which pages to generate based on data availability, and creates appropriate side-specific and combined pages. See the `SomaDetectionService` and its `generate_pages_with_auto_detection` method in the relevant service files.

#### Detection Logic

The system uses sophisticated logic to determine which pages to generate based on soma side distribution, counting sides with data, and handling unknown soma side counts. See the `_should_generate_combined_page` function implementation for the complete logic.

#### Page Generation Scenarios

**Scenario 1: Multi-hemisphere neuron type (e.g., Dm4)**
- Data: 45 left neurons, 42 right neurons
- Generated pages: `Dm4_L.html`, `Dm4_R.html`, `Dm4.html` (combined)
- Rationale: Multiple hemispheres warrant both individual and combined views

**Scenario 2: Single-hemisphere neuron type (e.g., LC10)**
- Data: 0 left neurons, 23 right neurons
- Generated pages: `LC10_R.html` only
- Rationale: No combined page needed for single-hemisphere types

**Scenario 3: Mixed data with unknowns**
- Data: 15 left neurons, 8 unknown-side neurons
- Generated pages: `NeuronType_L.html`, `NeuronType.html` (combined)
- Rationale: Unknown neurons justify a combined view alongside specific side

**Scenario 4: No soma side information**
- Data: 30 neurons, all unknown sides
- Generated pages: `NeuronType.html` (combined only)
- Rationale: Without hemisphere data, only combined view is meaningful

#### System Integration

The automatic page generation system maintains backward compatibility while removing user-facing complexity. The `GeneratePageCommand` class has been simplified by removing the `soma_side` parameter, allowing the system to auto-detect appropriate pages to generate. See `src/neuview/models/page_generation.py` for the updated command structure.

#### Performance Considerations

- **Data Analysis**: Single query analyzes all soma sides simultaneously
- **Parallel Generation**: Individual pages generated concurrently when possible
- **Cache Efficiency**: Shared data fetching across multiple page generations
- **Memory Management**: Automatic cleanup after page generation completes

### ROI Query Strategies

Different strategies for querying region of interest data:

**ROI Query Strategies** (`src/neuview/services/roi_analysis_service.py`):
- Strategy pattern for region-specific ROI queries
- Methods: `query_central_brain_rois()`, `categorize_rois()`
- Handles different brain region categorizations

## Visualization System

### Hexagon Grid Generator

**HexagonGridGenerator** (`src/neuview/services/visualization/hexagon_grid_generator.py`):
- Generates spatial visualizations for neuron distribution
- Configurable hex size and spacing parameters
- Key methods: `generate_region_hexagonal_grids()`, `generate_single_region_grid()`
- Outputs SVG format for web display

### Coordinate System

**Coordinate Functions** (`src/neuview/services/visualization/coordinate_utils.py`):
- Mathematical functions for hexagonal grid coordinate conversion
- Key functions: `hex_to_axial()`, `axial_to_pixel()`
- Handles hexagonal to Cartesian coordinate transformations

### Color Mapping

**Color Mapping Functions** (`src/neuview/services/visualization/color_utils.py`):
- Dynamic color assignment based on data values
- Key function: `get_color_for_value()`
- Supports multiple color schemes (viridis, plasma)
- Handles edge cases like constant values

## Template System

### Template Architecture

**Template Strategy Pattern** (`src/neuview/services/template_service.py`):
- Jinja2-based template system with custom extensions
- `TemplateStrategy` - Abstract base class for template handling
- `JinjaTemplateStrategy` - Jinja2 implementation with custom filters
- Key methods: `load_template()`, `render_template()`, `_setup_filters()`
- Custom filters registered for number formatting and URL safety

### Template Structure

**Template Organization** (`templates/` directory):
- `base.html.jinja` - Base layout template
- `neuron-page.html.jinja` - Individual neuron type pages
- `index.html.jinja` - Main index with search functionality
- `types.html.jinja` - Neuron type listing pages
- `static/js/` - JavaScript template files (neuroglancer integration, page interactions)
- `static/css/` - CSS template files with dynamic styling

### Template Context

**Template Context Management** (`src/neuview/services/template_context_service.py`):
- Structured data preparation for template rendering
- `TemplateContext` class organizing neuron, connectivity, ROI, and visualization data
- Key method: `to_dict()` for template consumption
- Handles data serialization and context validation

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

**Connectivity Tables** (`templates/sections/connectivity_table.html.jinja`):
- Handles CV display with proper fallbacks for coefficient of variation data
- Safe fallback patterns using Jinja2 `get()` method with default values
- Descriptive tooltips for CV column explaining statistical meaning
- Consistent implementation across upstream and downstream tables
- Custom filters for number and percentage formatting

### Custom Template Filters

**Template Filters** (`src/neuview/services/template_service.py`):
- `format_number_filter()` - Formats numbers with precision and thousand separators (K, M suffixes)
- `format_percentage()` - Handles percentage formatting with appropriate precision
- `safe_url()` - URL encoding and sanitization for dynamic links
- Registered automatically during Jinja2 environment setup

## Performance & Caching

### Multi-Level Cache System

neuView implements a sophisticated caching system with multiple levels:

**CacheService** (`src/neuview/services/cache_service.py`):
- Multi-level caching system with memory, file, and database backends
- Key method: `get_cached_data()` with fallback chain across cache levels
- Automatic cache population and eviction policies
- Backend implementations in respective cache backend modules

### Cache Types

- **Memory Cache**: In-memory LRU cache for immediate access
- **File Cache**: Persistent file-based cache surviving process restarts
- **Database Cache**: SQLite-based cache for complex queries
- **HTTP Cache**: Response caching for NeuPrint API calls

### Performance Optimizations

Key optimizations implemented:

- **Database Connection Pooling**: Reuse connections across requests
- **Batch Query Processing**: Combine multiple queries into single requests
- **Lazy Loading**: Load data only when needed
- **Asynchronous Processing**: Non-blocking I/O for improved throughput
- **Compressed Storage**: Gzip compression for cached data

### Performance Monitoring

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

#### Migration Considerations

When updating cache locations:

1. **Automatic Migration**: Cache files regenerate automatically from sources
2. **No Data Loss**: Old cache files can be safely removed
3. **Backward Compatibility**: Fallback paths maintain functionality
4. **Clean Transition**: Remove old cache files after verification

**Migration Pattern**: Services support automatic migration from previous cache locations. The ROI Data Service demonstrates output directory adoption with automatic cleanup.

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

### Overview

neuView uses a comprehensive testing strategy with clear separation between unit and integration tests. Tests are organized by type and use pytest markers for selective execution.

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)
Fast, isolated tests that focus on individual components without external dependencies.

**Characteristics:**
- Fast execution (< 1 second total)
- No file I/O operations
- No external service dependencies
- Test single methods/functions
- Mock external dependencies when needed

**Example:**
```python
@pytest.mark.unit
class TestDatasetAdapterFactory:
    """Unit tests for DatasetAdapterFactory."""

    @pytest.mark.unit
**Example Unit Test** (`test/test_dataset_adapters.py`):
- `TestDatasetAdapterFactory.test_male_cns_alias_resolution()` - Tests adapter factory with dataset aliases
- Verifies that "male-cns" resolves to correct CNSAdapter instance
```

#### Integration Tests (`@pytest.mark.integration`)
End-to-end tests that verify component interactions and real-world scenarios.

**Characteristics:**
- Slower execution (may involve file I/O)
- Test component interactions
- Uses real configuration files
- Tests end-to-end workflows
- May use temporary files/resources

**Example Integration Test** (`test/test_male_cns_integration.py`):
- `TestMaleCNSIntegration.test_config_with_male_cns_creates_cns_adapter()` - End-to-end configuration testing
- Creates temporary config files and tests full component integration
- Validates that configuration properly creates expected adapter instances

### Test Execution

#### Test Execution Commands

**Test execution tasks are defined in `pixi.toml`:**
- Unit tests: `pixi run unit-test` (fast feedback)
- Integration tests: `pixi run integration-test` (comprehensive testing)
- All tests: `pixi run test` (complete test suite)
- Coverage reports: `pixi run test-coverage`
- Verbose output: Add `-verbose` suffix to any test command

**Selective execution supports targeting specific files, classes, or methods using pytest syntax.**

### Test Structure

**Test Organization** (`test/` directory):
- `test_dataset_adapters.py` - Unit tests for factory and adapters
- `test_male_cns_integration.py` - Integration tests for end-to-end scenarios
- `services/` - Service-specific test modules
- `visualization/` - Visualization component tests
- `fixtures/` - Test data and fixture files

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

### Test Data and Fixtures

#### Unit Test Data
- Hardcoded test values for predictable behavior
- Use of mock objects for external dependencies
- Parameterized tests for multiple similar scenarios

#### Integration Test Data
- Temporary configuration files created during test execution
- Real project configuration files when available
- Cleanup of temporary resources after tests

### Dataset Alias Testing

**Dataset Alias Testing**: Special focus on testing dataset alias functionality with comprehensive test cases for versioned aliases. See `test_male_cns_versioned_alias_resolution()` and `test_end_to_end_male_cns_workflow()` in test files for reference implementations.

### Debugging Failed Tests

#### Unit Test Failures
Run specific failing tests with verbose output using pytest selection syntax. Check test markers to understand test categorization.

#### Integration Test Failures
Verify environment setup, token configuration, and run tests with verbose debugging and traceback options to diagnose integration test issues.

### Adding New Tests

When adding new features:

1. **Add unit tests** for individual components
2. **Add integration tests** if the feature involves multiple components
3. **Use appropriate markers** (`@pytest.mark.unit` or `@pytest.mark.integration`)
4. **Follow naming conventions**
5. **Ensure proper cleanup** of resources in integration tests

### Test Data Factory

**TestDataFactory** (`test/fixtures/test_data_factory.py`):
- Centralized test data creation for consistent testing
- Key methods: `create_neuron_data()`, `create_connectivity_data()`
- Provides standardized test data structures for neuron and connectivity testing
- Parameterizable factory methods for different test scenarios

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

**Configuration Structure** (`config.yaml` and `src/neuview/config/config.py`):
- YAML-based configuration system with hierarchical structure
- Key sections: neuprint, cache, templates, performance, visualization
- Reference configuration examples in project root `config.yaml`
- Configuration dataclasses define structure and validation rules

### Environment Variables

Environment variable support for sensitive configuration:

- `NEUPRINT_APPLICATION_CREDENTIALS`: NeuPrint API token
- `NEUVIEW_CONFIG_PATH`: Custom configuration file path
- `NEUVIEW_CACHE_DIR`: Cache directory override
- `NEUVIEW_DEBUG`: Enable debug logging
- `NEUVIEW_PROFILE`: Enable performance profiling

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

FAFB (FlyWire Adult Fly Brain) requires special handling due to data structure differences:

#### Soma Side Property Differences

FAFB stores soma side information differently than other datasets:

**Standard Datasets (CNS, Hemibrain)**:
- Property: `somaSide`
- Values: "L", "R", "M"

**FAFB Dataset**:
- Property: `side` OR `somaSide`
- Values: "LEFT", "RIGHT", "CENTER" or "left", "right", "center"

#### FAFB Adapter Implementation

**FAFBAdapter** (`src/neuview/services/dataset_adapters/fafb_adapter.py`):
- Custom soma side extraction handling FAFB-specific property differences
- `extract_soma_side()` method with fallback logic for `somaSide` vs `side` properties
- Property value mapping: LEFT/RIGHT → L/R, CENTER/MIDDLE → C
- Handles case variations and FAFB-specific nomenclature

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

The Dynamic ROI Data System replaces hardcoded ROI arrays in Neuroglancer templates with live data fetched from Google Cloud Storage, ensuring ROI information is always up-to-date.

#### Problem Statement

Previously, the `neuroglancer-url-generator.js.jinja` template contained hardcoded arrays:

```javascript
// Hardcoded ROI data (maintenance burden)
const ROI_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ...];
const ALL_ROIS = ["AL(L)", "AL(R)", "AME(L)", "AME(R)", ...];
const VNC_IDS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, ...];
const VNC_NAMES = ["CV-posterior", "LegNp(T1)(L)", ...];
```

This approach had significant drawbacks:
- **Manual Maintenance**: Required manual updates when ROI data changed
- **Data Inconsistency**: Risk of hardcoded data becoming stale
- **Version Mismatch**: Potential conflicts between different dataset versions

#### Solution Architecture

The system now uses a `ROIDataService` that:

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

#### Jinja Template Processing Fix

A critical bug was resolved where Jinja placeholders weren't being processed correctly.

**Problem**: The entire JavaScript template was wrapped in `{% raw %}` tags, preventing Jinja expression processing:

```javascript
// Template variables (processed)
const NEUROGLANCER_BASE_URL = "{{ neuroglancer_base_url }}";

{% raw %}
// Everything here is literal text - Jinja expressions NOT processed
const ROI_IDS = {{ roi_ids|tojson }};  // ❌ Not processed!
{% endraw %}
```

**Solution**: Moved ROI data declarations outside the `{% raw %}` block:

```javascript
// Template variables (processed by Jinja)
const NEUROGLANCER_BASE_URL = "{{ neuroglancer_base_url }}";
const ROI_IDS = {{ roi_ids|tojson }};
const ALL_ROIS = {{ all_rois|tojson }};

{% raw %}
// Static JavaScript code (not processed by Jinja)
// ... rest of JavaScript
{% endraw %}
```

#### ROI ID Collision Fix

A sophisticated fix was implemented to resolve ROI ID collisions between brain and VNC datasets.

**Problem**: ROI segment IDs overlap between datasets:
- ID 7: "AOTU(L)" in brain dataset, "LegNp(T2)(L)" in VNC dataset
- Clicking brain ROI checkboxes incorrectly toggled VNC layers

**Root Cause**: Layer assignment logic used only ID values without dataset context:

```javascript
// Problematic code
if (VNC_IDS.includes(parseInt(roiId))) {
    // Always assigned to VNC layer, even for brain ROIs with same ID
}
```

**Solution**: Introduced context tracking with `selectedRoiContexts` map:

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

#### Future Enhancements

Planned improvements:
1. **Filter Combinations**: Allow synonym AND Flywire filters simultaneously
2. **Filter Persistence**: Save filter state in URL parameters
3. **Advanced Search**: Boolean operators for complex queries
4. **Performance**: Virtual scrolling for large datasets


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

### Neuroglancer Integration Fixes

#### Problem
Neuroglancer JavaScript errors due to placeholder mismatches:

**Problem**: Neuroglancer JavaScript errors due to placeholder type mismatches with expected array format.

#### Solution
**Template Variable Correction** (`src/neuview/services/neuroglancer_js_service.py`):
- Correct placeholder types in template generation
- Empty array initialization instead of string placeholders
- Proper JSON array format for Neuroglancer compatibility

#### Flexible Dataset Layer Detection

**Multi-Dataset Layer Detection** (`templates/static/js/neuroglancer-url-generator.js.jinja`):
- Enhanced layer detection logic for multiple dataset types
- Flexible segmentation layer identification by type and properties
- Support for both CNS ("cns-seg") and FAFB ("flywire-fafb:v783b") layer names

### HTML Tooltip System Implementation

Rich tooltips for enhanced user experience:

#### Basic Structure

**HTML Tooltip Structure** (`templates/sections/tooltips.html.jinja`):
- Rich HTML content containers with formatted text, lists, and styling
- Tooltip content wrapper with trigger elements
- Flexible content structure supporting headings, paragraphs, and lists

#### JavaScript Implementation

**Tooltip JavaScript** (`templates/static/js/tooltip-system.js`):
- `initializeHtmlTooltips()` - Sets up event listeners for tooltip elements
- `positionTooltip()` - Dynamic positioning with screen boundary detection
- Mouseenter/mouseleave event handling for show/hide behavior
- Automatic positioning adjustment to prevent off-screen display

## Troubleshooting

### Common Issues

#### NeuPrint Connection Failures

**Symptoms**:
- Connection timeout errors
- Authentication failures
- Dataset not found errors

**Debugging**:
```bash
# Test connection
neuview test-connection

# Check configuration
neuview --verbose test-connection

# Verify token
echo $NEUPRINT_APPLICATION_CREDENTIALS
```

**Solutions**:
- Verify NeuPrint token is valid and not expired
- Check network connectivity to neuprint.janelia.org
- Ensure dataset name matches exactly (case-sensitive)
- Try different NeuPrint server endpoints

#### Template Rendering Errors

**Symptoms**:
- Jinja2 template syntax errors
- Missing template files
- Context variable errors

**Debugging**:
```python
def validate_template(template_path: str) -> Result[bool]:
    """Validate template syntax and required variables."""
    try:
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))

        # Test render with minimal context
        template.render({})
        return Result.success(True)
    except Exception as e:
        return Result.failure(f"Template error: {e}")
```

**Solutions**:
- Check template syntax with Jinja2 linter
- Verify all required template variables are provided
- Check file permissions on template directory
- Ensure template inheritance chain is correct

#### Cache Issues

**Symptoms**:
- Stale data being served
- Cache corruption errors
- Excessive memory usage

**Solutions**:
```bash
# Clear all caches manually
rm -rf output/.cache/

# Check cache directory contents
ls -la output/.cache/

# Check cache file sizes
du -sh output/.cache/*
```

#### Performance Issues

**Symptoms**:
- Slow page generation
- High memory usage
- Database timeouts

**Investigation**:
- Enable performance profiling: `NEUVIEW_PROFILE=1`
- Check cache hit rates
- Monitor database query performance
- Review memory usage patterns

### Debugging Tools

#### Log Configuration

Enable detailed logging:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
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

Enable development mode by setting the `NEUVIEW_DEBUG` and `NEUVIEW_PROFILE` environment variables and running neuview with the `--verbose` flag.

This enables:
- Detailed operation logging
- Performance timing information
- Memory usage tracking
- Cache operation details
- Database query logging

### Logging Architecture

neuView uses a multi-layer logging system for different concerns including main application logging and dedicated citation logging with isolated loggers.

#### System Loggers

The system uses separate loggers for main application events and citation tracking. See the logging configuration in the service files for logger setup and configuration.

#### Citation Logging Implementation

The citation logging system automatically tracks missing citations with dedicated logger setup, log directory creation, file rotation handling, and custom formatting. See the `_setup_citation_logger` method in the citation service for the complete implementation including rotating file handlers and UTF-8 encoding support.

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

### Code Style

Follow these coding standards:

- **PEP 8**: Python code style guide
- **Type Hints**: Use type annotations for all public APIs
- **Docstrings**: Google-style docstrings for all classes and functions
- **Error Handling**: Use Result pattern for fallible operations
- **Testing**: Minimum 90% test coverage for new code

### Pull Request Process

1. **Fork** the repository and create a feature branch
2. **Implement** changes following coding standards
3. **Test** thoroughly with unit and integration tests
4. **Document** changes in relevant documentation files
5. **Submit** pull request with clear description of changes

### Development Workflow

#### Setting Up Development Environment

Clone the repository, install dependencies with pixi, create feature branches using git, and install pre-commit hooks for code quality.

#### Running Tests

Run various test suites including unit tests, coverage reporting, integration tests, and performance tests using the appropriate pixi run commands.

### Adding New Services

When adding new services, follow this pattern:

1. **Define Interface**: Create abstract base class defining the service contract
2. **Implement Service**: Create concrete implementation with proper error handling
3. **Register Service**: Add to service container factory
4. **Write Tests**: Comprehensive unit and integration tests
5. **Update Documentation**: Add to this developer guide

### Performance Considerations

When contributing code:

- **Cache Appropriately**: Use existing cache layers for expensive operations
- **Minimize Database Queries**: Batch queries when possible
- **Handle Large Datasets**: Consider memory usage for large neuron types
- **Profile Changes**: Use performance profiling to verify no regressions
- **Optimize Critical Paths**: Focus on page generation performance

---

This developer guide provides comprehensive coverage of neuView's architecture, implementation patterns, and development practices. For user-focused documentation, see the [User Guide](user-guide.md).
