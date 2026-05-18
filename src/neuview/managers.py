"""
Manager Classes for neuView Phase 3

This module provides high-level manager classes that orchestrate the various
strategies for template and resource management. These managers provide a
unified interface for complex operations while leveraging the strategy pattern
for flexibility and extensibility.

Managers:
- TemplateManager: Orchestrates template loading, caching, and rendering
- ResourceManager: Orchestrates resource loading, caching, and optimization
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Set, Union
from collections import defaultdict

from .strategies import (
    TemplateStrategy,
    ResourceStrategy,
    TemplateError,
    TemplateNotFoundError,
    ResourceNotFoundError,
)
from .strategies.template import JinjaTemplateStrategy, StaticTemplateStrategy
from .strategies.resource import UnifiedResourceStrategy, CompositeResourceStrategy
from .strategies.cache import (
    MemoryCacheStrategy,
    FileCacheStrategy,
    CompositeCacheStrategy,
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    High-level template manager that orchestrates template strategies.

    This manager provides a unified interface for template operations while
    leveraging different strategies for optimal performance and flexibility.
    """

    def __init__(self, template_dir: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize template manager.

        Args:
            template_dir: Base directory containing templates
            config: Configuration options for template management
        """
        self.template_dir = Path(template_dir)
        self.config = config or {}

        # Initialize strategies
        self._primary_strategy = None
        self._fallback_strategies = []
        self._cache_strategy = None

        # Template tracking
        self._template_cache = {}
        self._dependency_graph = defaultdict(set)
        self._reverse_dependency_graph = defaultdict(set)
        self._validation_cache = {}

        # Performance monitoring
        self._load_times = {}
        self._render_times = {}
        self._cache_hits = 0
        self._cache_misses = 0

        self._setup_default_strategies()

    def _setup_default_strategies(self) -> None:
        """Set up default template strategies based on configuration."""
        # Set up caching
        cache_config = self.config.get("cache", {})
        if cache_config.get("enabled", True):
            cache_type = cache_config.get("type", "memory")

            if cache_type == "memory":
                self._cache_strategy = MemoryCacheStrategy(
                    max_size=cache_config.get("max_size", 1000),
                    default_ttl=cache_config.get("ttl", 3600),
                )
            elif cache_type == "file":
                cache_dir = Path(cache_config.get("dir", self.template_dir / ".cache"))
                self._cache_strategy = FileCacheStrategy(
                    cache_dir=str(cache_dir), default_ttl=cache_config.get("ttl", 3600)
                )
            elif cache_type == "composite":
                memory_cache = MemoryCacheStrategy(max_size=100)
                file_cache = FileCacheStrategy(
                    cache_dir=str(
                        Path(cache_config.get("dir", self.template_dir / ".cache"))
                    )
                )
                self._cache_strategy = CompositeCacheStrategy(memory_cache, file_cache)

        # Set up primary template strategy
        template_config = self.config.get("template", {})
        strategy_type = template_config.get("type", "auto")

        if strategy_type == "jinja" or strategy_type == "auto":
            try:
                self._primary_strategy = JinjaTemplateStrategy(
                    template_dirs=[str(self.template_dir)],
                    auto_reload=template_config.get("auto_reload", True),
                    cache_size=template_config.get("cache_size", 400),
                )

            except Exception as e:
                logger.warning(f"Failed to initialize Jinja strategy: {e}")
                if strategy_type == "jinja":
                    raise

        # Add static strategy only when explicitly requested or as emergency fallback
        if strategy_type == "static":
            static_strategy = StaticTemplateStrategy([str(self.template_dir)])
            self._primary_strategy = static_strategy
        elif strategy_type == "auto" and not self._primary_strategy:
            # Only add static as fallback if no primary strategy was set up
            static_strategy = StaticTemplateStrategy([str(self.template_dir)])
            self._fallback_strategies.append(static_strategy)

    def register_strategy(
        self, strategy: TemplateStrategy, is_primary: bool = False
    ) -> None:
        """
        Register a custom template strategy.

        Args:
            strategy: Template strategy to register
            is_primary: Whether this should be the primary strategy
        """
        if is_primary:
            self._primary_strategy = strategy
        else:
            self._fallback_strategies.append(strategy)

    def load_template(self, template_path: str) -> Any:
        """
        Load a template using the configured strategies.

        Args:
            template_path: Path to the template file

        Returns:
            Template object that can be used for rendering

        Raises:
            TemplateNotFoundError: If template cannot be found by any strategy
        """
        import time

        start_time = time.time()

        # Check cache first if caching is enabled
        cache_key = f"template:{template_path}"
        if self._cache_strategy:
            cached_template = self._cache_strategy.get(cache_key)
            if cached_template is not None:
                self._cache_hits += 1
                return cached_template

        # Also check local template cache
        if cache_key in self._template_cache:
            self._cache_hits += 1
            return self._template_cache[cache_key]

        self._cache_misses += 1

        # Try to select the best strategy for this template
        strategies_to_try = []

        # Check if primary strategy supports this template
        if self._primary_strategy:
            if hasattr(self._primary_strategy, "supports_template"):
                if self._primary_strategy.supports_template(template_path):
                    strategies_to_try.append(self._primary_strategy)
            else:
                strategies_to_try.append(self._primary_strategy)

        # Add fallback strategies that support this template
        for strategy in self._fallback_strategies:
            if hasattr(strategy, "supports_template"):
                if strategy.supports_template(template_path):
                    strategies_to_try.append(strategy)
            else:
                strategies_to_try.append(strategy)

        # If no strategies were added based on support, use all available strategies
        if not strategies_to_try:
            if self._primary_strategy:
                strategies_to_try.append(self._primary_strategy)
            strategies_to_try.extend(self._fallback_strategies)

        # Try strategies in order
        for strategy in strategies_to_try:
            try:
                template = strategy.load_template(template_path)

                # Cache the template
                self._template_cache[cache_key] = template
                if self._cache_strategy:
                    cache_ttl = self.config.get("cache", {}).get("ttl", 3600)
                    self._cache_strategy.put(cache_key, template, cache_ttl)

                self._load_times[template_path] = time.time() - start_time
                return template
            except TemplateNotFoundError:
                continue
            except Exception as e:
                logger.error(
                    f"Strategy {strategy.__class__.__name__} failed for {template_path}: {e}"
                )
                continue

        raise TemplateNotFoundError(f"Template not found: {template_path}")

    def render_template(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_path: Path to the template file
            context: Variables to pass to the template

        Returns:
            Rendered template content

        Raises:
            TemplateNotFoundError: If template cannot be found
            TemplateRenderError: If rendering fails
        """
        import time
        import hashlib

        start_time = time.time()

        # Check rendered cache if enabled
        if self._cache_strategy:
            # Generate cache key based on template and context
            context_hash = hashlib.md5(
                str(sorted(context.items())).encode()
            ).hexdigest()
            render_cache_key = f"rendered:{template_path}:{context_hash}"

            cached_result = self._cache_strategy.get(render_cache_key)
            if cached_result is not None:
                return cached_result

        template = self.load_template(template_path)

        # Determine which strategy to use for rendering
        strategy = self._primary_strategy
        if not strategy:
            strategy = (
                self._fallback_strategies[0] if self._fallback_strategies else None
            )

        if not strategy:
            raise TemplateError("No template strategy available for rendering")

        try:
            result = strategy.render_template(template, context)
            self._render_times[template_path] = time.time() - start_time

            # Cache the rendered result if caching is enabled
            if self._cache_strategy:
                context_hash = hashlib.md5(
                    str(sorted(context.items())).encode()
                ).hexdigest()
                render_cache_key = f"rendered:{template_path}:{context_hash}"
                # Use shorter TTL for rendered content
                render_ttl = min(self.config.get("cache", {}).get("ttl", 3600), 1800)
                self._cache_strategy.put(render_cache_key, result, render_ttl)

            return result
        except Exception as e:
            raise TemplateError(f"Failed to render template {template_path}: {e}")

    def validate_template(self, template_path: str) -> bool:
        """
        Validate that a template is syntactically correct.

        Args:
            template_path: Path to the template file

        Returns:
            True if template is valid, False otherwise
        """
        # Check cache first
        validation_cache_key = f"validation:{template_path}"
        if self._cache_strategy:
            cached_result = self._cache_strategy.get(validation_cache_key)
            if cached_result is not None:
                return cached_result

        if template_path in self._validation_cache:
            return self._validation_cache[template_path]

        # Try primary strategy first
        if self._primary_strategy:
            try:
                result = self._primary_strategy.validate_template(template_path)
                self._validation_cache[template_path] = result

                # Cache validation result
                if self._cache_strategy:
                    validation_ttl = min(
                        self.config.get("cache", {}).get("ttl", 3600), 600
                    )
                    self._cache_strategy.put(
                        validation_cache_key, result, validation_ttl
                    )

                return result
            except Exception:
                pass

        # Try fallback strategies
        for strategy in self._fallback_strategies:
            try:
                result = strategy.validate_template(template_path)
                self._validation_cache[template_path] = result

                # Cache validation result
                if self._cache_strategy:
                    validation_ttl = min(
                        self.config.get("cache", {}).get("ttl", 3600), 600
                    )
                    self._cache_strategy.put(
                        validation_cache_key, result, validation_ttl
                    )

                return result
            except Exception:
                continue

        self._validation_cache[template_path] = False

        # Cache negative result too
        if self._cache_strategy:
            validation_ttl = min(self.config.get("cache", {}).get("ttl", 3600), 600)
            self._cache_strategy.put(validation_cache_key, False, validation_ttl)

        return False

    def list_templates(self, pattern: str = "*.jinja") -> List[str]:
        """
        List all available templates.

        Args:
            pattern: Glob pattern to match template files

        Returns:
            List of template paths
        """
        all_templates = set()

        # Get templates from primary strategy
        if self._primary_strategy:
            try:
                templates = self._primary_strategy.list_templates(self.template_dir)
                all_templates.update(templates)
            except Exception as e:
                logger.error(f"Failed to list templates with primary strategy: {e}")

        # Get templates from fallback strategies
        for strategy in self._fallback_strategies:
            try:
                templates = strategy.list_templates(self.template_dir)
                all_templates.update(templates)
            except Exception as e:
                logger.error(f"Failed to list templates with fallback strategy: {e}")

        # Filter by pattern if specified
        if pattern != "*":
            import fnmatch

            all_templates = {t for t in all_templates if fnmatch.fnmatch(t, pattern)}

        return sorted(list(all_templates))

    def get_template_dependencies(self, template_path: str) -> List[str]:
        """
        Get all dependencies for a template.

        Args:
            template_path: Path to the template file

        Returns:
            List of dependency template paths
        """
        if template_path in self._dependency_graph:
            return list(self._dependency_graph[template_path])

        dependencies = set()

        # Get dependencies from primary strategy
        if self._primary_strategy:
            try:
                deps = self._primary_strategy.get_template_dependencies(template_path)
                dependencies.update(deps)
            except Exception as e:
                logger.error(f"Failed to get dependencies with primary strategy: {e}")

        # Get dependencies from fallback strategies
        for strategy in self._fallback_strategies:
            try:
                deps = strategy.get_template_dependencies(template_path)
                dependencies.update(deps)
            except Exception as e:
                logger.error(f"Failed to get dependencies with fallback strategy: {e}")

        # Cache dependencies
        self._dependency_graph[template_path] = dependencies

        # Update reverse dependency graph
        for dep in dependencies:
            self._reverse_dependency_graph[dep].add(template_path)

        return list(dependencies)


    def _find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the template graph."""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(template, path):
            if template in rec_stack:
                # Found a cycle
                cycle_start = path.index(template)
                cycle = path[cycle_start:] + [template]
                cycles.append(cycle)
                return

            if template in visited:
                return

            visited.add(template)
            rec_stack.add(template)
            path.append(template)

            for dep in self._dependency_graph.get(template, []):
                dfs(dep, path[:])

            rec_stack.remove(template)
            path.pop()

        for template in self._dependency_graph:
            if template not in visited:
                dfs(template, [])

        return cycles

    def invalidate_template(self, template_path: str) -> None:
        """
        Invalidate cache for a specific template and its dependents.

        Args:
            template_path: Path to the template file
        """
        # Remove from local caches
        cache_key = f"template:{template_path}"
        if cache_key in self._template_cache:
            del self._template_cache[cache_key]

        if template_path in self._validation_cache:
            del self._validation_cache[template_path]

        # Remove from cache strategy if available
        if self._cache_strategy:
            # Remove template cache
            self._cache_strategy.delete(cache_key)

            # Remove validation cache
            validation_cache_key = f"validation:{template_path}"
            self._cache_strategy.delete(validation_cache_key)

            # Remove any rendered templates (this is approximate - we can't get all context hashes)
            # In practice, rendered templates will expire naturally due to TTL

        # Invalidate dependents recursively
        dependents = self._reverse_dependency_graph.get(template_path, set())
        for dependent in dependents:
            self.invalidate_template(dependent)

    def clear_cache(self) -> None:
        """Clear all template caches."""
        self._template_cache.clear()
        self._validation_cache.clear()
        self._dependency_graph.clear()
        self._reverse_dependency_graph.clear()

        # Clear cache strategy if available
        if self._cache_strategy:
            # Clear everything (cache strategies don't support pattern clearing)
            self._cache_strategy.clear()



    def add_custom_filter(self, name: str, filter_func: callable) -> None:
        """
        Add a custom filter to template strategies that support it.

        Args:
            name: Name of the filter
            filter_func: Function to use as filter
        """
        if self._primary_strategy and hasattr(self._primary_strategy, "add_filter"):
            self._primary_strategy.add_filter(name, filter_func)

        for strategy in self._fallback_strategies:
            if hasattr(strategy, "add_filter"):
                strategy.add_filter(name, filter_func)

    def add_global_variable(self, name: str, value: Any) -> None:
        """
        Add a global variable to template strategies that support it.

        Args:
            name: Name of the global variable
            value: Value of the global variable
        """
        if self._primary_strategy and hasattr(self._primary_strategy, "add_global"):
            self._primary_strategy.add_global(name, value)

        for strategy in self._fallback_strategies:
            if hasattr(strategy, "add_global"):
                strategy.add_global(name, value)


    def get_template_info(self, template_path: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a template.

        Args:
            template_path: Path to the template file

        Returns:
            Dictionary containing template information
        """
        info = {
            "path": template_path,
            "exists": False,
            "valid": False,
            "dependencies": [],
            "dependents": [],
            "load_time": None,
            "render_time": None,
            "cached": False,
        }

        try:
            # Check existence and validity
            info["exists"] = True
            info["valid"] = self.validate_template(template_path)

            # Get dependencies
            info["dependencies"] = self.get_template_dependencies(template_path)
            info["dependents"] = list(
                self._reverse_dependency_graph.get(template_path, set())
            )

            # Get performance info
            info["load_time"] = self._load_times.get(template_path)
            info["render_time"] = self._render_times.get(template_path)

            # Check if cached
            cache_key = f"template:{template_path}"
            info["cached"] = cache_key in self._template_cache

        except TemplateNotFoundError:
            pass
        except Exception as e:
            info["error"] = str(e)

        return info


class ResourceManager:
    """
    High-level resource manager that orchestrates resource strategies.

    This manager provides a unified interface for resource operations while
    leveraging different strategies for optimal performance and flexibility.
    """

    def __init__(
        self,
        base_paths: Union[Path, List[Path]],
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize resource manager.

        Args:
            base_paths: Base directory or list of directories containing resources
            config: Configuration options for resource management
        """
        if isinstance(base_paths, (str, Path)):
            self.base_paths = [Path(base_paths)]
        else:
            self.base_paths = [Path(d) for d in base_paths]

        self.config = config or {}

        # Initialize strategies
        self._primary_strategy = None
        self._fallback_strategies = []
        self._cache_strategy = None

        # Resource tracking
        self._resource_cache = {}
        self._metadata_cache = {}
        self._dependency_graph = defaultdict(set)

        # Performance monitoring
        self._load_times = {}
        self._cache_hits = 0
        self._cache_misses = 0

        self._setup_default_strategies()

    def _setup_default_strategies(self) -> None:
        """Set up default resource strategies based on configuration."""
        # Set up caching
        cache_config = self.config.get("cache", {})
        if cache_config.get("enabled", True):
            cache_type = cache_config.get("type", "memory")

            if cache_type == "memory":
                self._cache_strategy = MemoryCacheStrategy(
                    max_size=cache_config.get("max_size", 500),
                    default_ttl=cache_config.get("ttl", 7200),
                )
            elif cache_type == "file":
                cache_dir = Path(cache_config.get("dir", self.base_paths[0] / ".cache"))
                self._cache_strategy = FileCacheStrategy(
                    cache_dir=str(cache_dir), default_ttl=cache_config.get("ttl", 3600)
                )
            elif cache_type == "composite":
                memory_cache = MemoryCacheStrategy(max_size=100)
                file_cache = FileCacheStrategy(
                    cache_dir=str(
                        Path(cache_config.get("dir", self.base_paths[0] / ".cache"))
                    )
                )
                self._cache_strategy = CompositeCacheStrategy(memory_cache, file_cache)

        # Set up primary resource strategy
        resource_config = self.config.get("resource", {})
        strategy_type = resource_config.get("type", "unified")

        if strategy_type == "unified":
            # New unified strategy that combines filesystem, caching, and optimization
            self._primary_strategy = UnifiedResourceStrategy(
                base_paths=[str(path) for path in self.base_paths],
                follow_symlinks=resource_config.get("follow_symlinks", True),
                cache_strategy=self._cache_strategy,
                cache_ttl=resource_config.get("cache_ttl", 3600),
                enable_optimization=resource_config.get(
                    "enable_optimization", resource_config.get("optimize", False)
                ),
                enable_minification=resource_config.get(
                    "enable_minification", resource_config.get("minify", True)
                ),
                enable_compression=resource_config.get(
                    "enable_compression", resource_config.get("compress", True)
                ),
                enable_metadata_cache=resource_config.get("metadata_cache", True),
            )
        elif strategy_type == "composite":
            # Set up composite strategy for mixed resource types
            composite_strategy = CompositeResourceStrategy()

            # Use unified strategy for local resources
            local_strategy = UnifiedResourceStrategy(
                base_paths=[str(path) for path in self.base_paths],
                follow_symlinks=resource_config.get("follow_symlinks", True),
                cache_strategy=self._cache_strategy,
                enable_optimization=resource_config.get(
                    "enable_optimization", resource_config.get("optimize", False)
                ),
                enable_minification=resource_config.get(
                    "enable_minification", resource_config.get("minify", True)
                ),
                enable_compression=resource_config.get(
                    "enable_compression", resource_config.get("compress", True)
                ),
            )
            composite_strategy.register_strategy(
                r"^(?!https?://)",  # Regex pattern for non-HTTP(S) paths
                local_strategy,
            )

            # Add remote strategy for HTTP resources
            from .strategies.resource import RemoteResourceStrategy

            remote_strategy = RemoteResourceStrategy(
                base_url="",  # Will be determined from the resource path
                timeout=resource_config.get("timeout", 30),
                max_retries=resource_config.get("max_retries", 3),
            )
            composite_strategy.register_strategy(
                r"^https?://",  # Regex pattern for HTTP(S) URLs
                remote_strategy,
            )

            composite_strategy.set_default_strategy(local_strategy)
            self._primary_strategy = composite_strategy

    def register_strategy(
        self, strategy: ResourceStrategy, is_primary: bool = False
    ) -> None:
        """
        Register a custom resource strategy.

        Args:
            strategy: Resource strategy to register
            is_primary: Whether this should be the primary strategy
        """
        if is_primary:
            self._primary_strategy = strategy
        else:
            self._fallback_strategies.append(strategy)

    def load_resource(self, resource_path: str) -> bytes:
        """
        Load a resource using the configured strategies.

        Args:
            resource_path: Path to the resource file

        Returns:
            Resource content as bytes

        Raises:
            ResourceNotFoundError: If resource cannot be found by any strategy
        """
        import time

        start_time = time.time()

        # Check cache first
        cache_key = f"resource:{resource_path}"
        if cache_key in self._resource_cache:
            self._cache_hits += 1
            return self._resource_cache[cache_key]

        self._cache_misses += 1

        # Try primary strategy first
        if self._primary_strategy:
            try:
                content = self._primary_strategy.load_resource(resource_path)
                self._resource_cache[cache_key] = content
                self._load_times[resource_path] = time.time() - start_time
                return content
            except ResourceNotFoundError:
                pass
            except Exception as e:
                logger.error(f"Primary strategy failed for {resource_path}: {e}")

        # Try fallback strategies
        for strategy in self._fallback_strategies:
            try:
                content = strategy.load_resource(resource_path)
                self._resource_cache[cache_key] = content
                self._load_times[resource_path] = time.time() - start_time
                return content
            except ResourceNotFoundError:
                continue
            except Exception as e:
                logger.error(f"Fallback strategy failed for {resource_path}: {e}")
                continue

        raise ResourceNotFoundError(f"Resource not found: {resource_path}")

    def resource_exists(self, resource_path: str) -> bool:
        """
        Check if a resource exists.

        Args:
            resource_path: Path to the resource file

        Returns:
            True if resource exists, False otherwise
        """
        # Try primary strategy first
        if self._primary_strategy:
            try:
                return self._primary_strategy.resource_exists(resource_path)
            except Exception as e:
                logger.error(
                    f"Primary strategy failed for existence check {resource_path}: {e}"
                )

        # Try fallback strategies
        for strategy in self._fallback_strategies:
            try:
                return strategy.resource_exists(resource_path)
            except Exception as e:
                logger.error(
                    f"Fallback strategy failed for existence check {resource_path}: {e}"
                )
                continue

        return False

    def get_resource_metadata(self, resource_path: str) -> Dict[str, Any]:
        """
        Get metadata for a resource.

        Args:
            resource_path: Path to the resource file

        Returns:
            Dictionary containing resource metadata

        Raises:
            ResourceNotFoundError: If resource cannot be found
        """
        if resource_path in self._metadata_cache:
            return self._metadata_cache[resource_path]

        # Try primary strategy first
        if self._primary_strategy:
            try:
                metadata = self._primary_strategy.get_resource_metadata(resource_path)
                self._metadata_cache[resource_path] = metadata
                return metadata
            except ResourceNotFoundError:
                pass
            except Exception as e:
                logger.error(
                    f"Primary strategy failed for metadata {resource_path}: {e}"
                )

        # Try fallback strategies
        for strategy in self._fallback_strategies:
            try:
                metadata = strategy.get_resource_metadata(resource_path)
                self._metadata_cache[resource_path] = metadata
                return metadata
            except ResourceNotFoundError:
                continue
            except Exception as e:
                logger.error(
                    f"Fallback strategy failed for metadata {resource_path}: {e}"
                )
                continue

        raise ResourceNotFoundError(f"Resource not found: {resource_path}")

    def list_resources(
        self, resource_dir: Optional[Path] = None, pattern: str = "*"
    ) -> List[str]:
        """
        List all available resources.

        Args:
            resource_dir: Specific directory to search (None for all directories)
            pattern: Glob pattern to match resource files

        Returns:
            List of resource paths
        """
        all_resources = set()
        search_dirs = [resource_dir] if resource_dir else self.base_paths

        for search_dir in search_dirs:
            # Get resources from primary strategy
            if self._primary_strategy:
                try:
                    resources = self._primary_strategy.list_resources(
                        search_dir, pattern
                    )
                    all_resources.update(resources)
                except Exception as e:
                    logger.error(f"Failed to list resources with primary strategy: {e}")

            # Get resources from fallback strategies
            for strategy in self._fallback_strategies:
                try:
                    resources = strategy.list_resources(search_dir, pattern)
                    all_resources.update(resources)
                except Exception as e:
                    logger.error(
                        f"Failed to list resources with fallback strategy: {e}"
                    )

        return sorted(list(all_resources))

    def copy_resource(self, source_path: str, dest_path: str) -> bool:
        """
        Copy a resource from source to destination.

        Args:
            source_path: Source resource path
            dest_path: Destination path

        Returns:
            True if copy was successful, False otherwise
        """
        # Try primary strategy first
        if self._primary_strategy:
            try:
                return self._primary_strategy.copy_resource(source_path, dest_path)
            except Exception as e:
                logger.error(f"Primary strategy failed for copy {source_path}: {e}")

        # Try fallback strategies
        for strategy in self._fallback_strategies:
            try:
                return strategy.copy_resource(source_path, dest_path)
            except Exception as e:
                logger.error(f"Fallback strategy failed for copy {source_path}: {e}")
                continue

        return False


    def invalidate_resource(self, resource_path: str) -> None:
        """
        Invalidate cache for a specific resource.

        Args:
            resource_path: Path to the resource file
        """
        # Remove from caches
        cache_key = f"resource:{resource_path}"
        if cache_key in self._resource_cache:
            del self._resource_cache[cache_key]

        if resource_path in self._metadata_cache:
            del self._metadata_cache[resource_path]

        # Invalidate cached resource strategy if applicable
        if self._primary_strategy and hasattr(
            self._primary_strategy, "invalidate_resource"
        ):
            self._primary_strategy.invalidate_resource(resource_path)

    def clear_cache(self) -> None:
        """Clear all resource caches."""
        self._resource_cache.clear()
        self._metadata_cache.clear()
        self._dependency_graph.clear()

        if self._primary_strategy and hasattr(self._primary_strategy, "clear_cache"):
            self._primary_strategy.clear_cache()

        for strategy in self._fallback_strategies:
            if hasattr(strategy, "clear_cache"):
                strategy.clear_cache()






class DependencyManager:
    """
    Manager for handling dependencies between templates and resources.

    This manager tracks and resolves dependencies between templates and resources,
    ensuring proper loading order and cache invalidation.
    """

    def __init__(
        self, template_manager: TemplateManager, resource_manager: ResourceManager
    ):
        """
        Initialize dependency manager.

        Args:
            template_manager: Template manager instance
            resource_manager: Resource manager instance
        """
        self.template_manager = template_manager
        self.resource_manager = resource_manager
        self._dependency_graph = defaultdict(set)
        self._reverse_dependency_graph = defaultdict(set)



    def get_dependents(self, item: str, item_type: str = "template") -> Set[str]:
        """
        Get all items that depend on the given item.

        Args:
            item: Item to get dependents for
            item_type: Type of the item ('template' or 'resource')

        Returns:
            Set of dependent items
        """
        dep_key = f"{item_type}:{item}"
        return self._reverse_dependency_graph.get(dep_key, set())


