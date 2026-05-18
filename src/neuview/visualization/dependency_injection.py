"""
Dependency injection container for the eyemap visualization module.

This module provides a comprehensive dependency injection system to manage
service creation, lifecycle, and dependencies throughout the eyemap generation
pipeline. It supports singleton services, factory patterns, and configuration-based
service resolution.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Type,
    TypeVar,
    Optional,
    Callable,
    Union,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from .color import ColorMapper
    from .coordinate_system import EyemapCoordinateSystem
    from .rendering import RenderingManager
    from .eyemap_generator import EyemapGenerator

# Configuration and exceptions are safe to import at module level
from .config_manager import ConfigurationManager, EyemapConfiguration
from .exceptions import DependencyError, ErrorContext

# Note: Other visualization module imports are done locally within methods
# to avoid circular dependencies. The following imports are kept local:
# - .color (ColorPalette, ColorMapper)
# - .coordinate_system (EyemapCoordinateSystem)
# - .data_processing (DataProcessor)
# - .rendering (RenderingManager)
# - .region_grid_processor (RegionGridProcessorFactory)
# - .file_output_manager (FileOutputManagerFactory)
# - .performance (PerformanceOptimizerFactory, get_performance_monitor, MemoryOptimizer)
# - .eyemap_generator (EyemapGenerator)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Defines the lifetime scope of services in the container."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """Describes how a service should be created and managed."""

    def __init__(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        dependencies: Optional[Dict[str, Union[Type, str]]] = None,
    ):
        """
        Initialize service descriptor.

        Args:
            service_type: The type of service this descriptor creates
            factory: Factory function to create the service
            lifetime: Service lifetime scope
            dependencies: Dictionary mapping parameter names to dependency types
        """
        self.service_type = service_type
        self.factory = factory
        self.lifetime = lifetime
        self.dependencies = dependencies or {}


class IServiceContainer(ABC):
    """Interface for dependency injection containers."""

    @abstractmethod
    def register(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        dependencies: Optional[Dict[str, Union[Type, str]]] = None,
    ) -> None:
        """Register a service with the container."""
        pass

    @abstractmethod
    def register_singleton(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        dependencies: Optional[Dict[str, Union[Type, str]]] = None,
    ) -> None:
        """Register a singleton service."""
        pass

    @abstractmethod
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Register a pre-created instance as a singleton."""
        pass

    @abstractmethod
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service from the container."""
        pass

    @abstractmethod
    def try_resolve(self, service_type: Type[T]) -> Optional[T]:
        """Try to resolve a service, returning None if not found."""
        pass

    @abstractmethod
    def is_registered(self, service_type: Type[T]) -> bool:
        """Check if a service type is registered."""
        pass


class VisualizationServiceContainer(IServiceContainer):
    """Concrete implementation of dependency injection container."""

    def __init__(self):
        """Initialize the service container."""
        self._descriptors: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._resolution_stack: List[Type] = []

    def register(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
        dependencies: Optional[Dict[str, Union[Type, str]]] = None,
    ) -> None:
        """
        Register a service with the container.

        Args:
            service_type: The type of service to register
            factory: Factory function to create instances
            lifetime: Service lifetime scope
            dependencies: Service dependencies mapping

        Raises:
            DependencyError: If registration fails
        """
        with ErrorContext("service_registration", service_type=service_type.__name__):
            if service_type in self._descriptors:
                logger.warning(
                    f"Overriding existing registration for {service_type.__name__}"
                )

            descriptor = ServiceDescriptor(
                service_type, factory, lifetime, dependencies
            )
            self._descriptors[service_type] = descriptor
            logger.debug(
                f"Registered {service_type.__name__} with {lifetime.value} lifetime"
            )

    def register_singleton(
        self,
        service_type: Type[T],
        factory: Callable[..., T],
        dependencies: Optional[Dict[str, Union[Type, str]]] = None,
    ) -> None:
        """
        Register a singleton service.

        Args:
            service_type: The type of service to register
            factory: Factory function to create the singleton instance
            dependencies: Service dependencies mapping
        """
        self.register(service_type, factory, ServiceLifetime.SINGLETON, dependencies)

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register a pre-created instance as a singleton.

        Args:
            service_type: The type of service
            instance: The pre-created instance

        Raises:
            DependencyError: If instance is not of expected type
        """
        with ErrorContext("instance_registration", service_type=service_type.__name__):
            if not isinstance(instance, service_type):
                raise DependencyError(
                    f"Instance is not of type {service_type.__name__}",
                    service_type=service_type.__name__,
                )

            # Register a factory that returns the instance
            self.register_singleton(service_type, lambda: instance)
            self._singletons[service_type] = instance
            logger.debug(f"Registered pre-created instance for {service_type.__name__}")

    def resolve(self, service_type: Union[Type[T], str]) -> T:
        """
        Resolve a service from the container.

        Args:
            service_type: The type of service to resolve or string name

        Returns:
            Instance of the requested service

        Raises:
            DependencyError: If service cannot be resolved
        """
        # Handle string-based resolution
        if isinstance(service_type, str):
            return self._resolve_by_string(service_type)

        service_name = service_type.__name__
        with ErrorContext("service_resolution", service_type=service_name):
            # Check for circular dependencies
            if service_type in self._resolution_stack:
                cycle = " -> ".join(
                    t.__name__ for t in self._resolution_stack + [service_type]
                )
                raise DependencyError(
                    f"Circular dependency detected: {cycle}",
                    service_type=service_name,
                    dependency_chain=[t.__name__ for t in self._resolution_stack]
                    + [service_name],
                )

            # Check if service is registered
            if service_type not in self._descriptors:
                raise DependencyError(
                    f"Service {service_name} is not registered",
                    service_type=service_name,
                )

            descriptor = self._descriptors[service_type]

            # Handle singleton lifetime
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._singletons:
                    return self._singletons[service_type]

            # Handle scoped lifetime
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                if service_type in self._scoped_instances:
                    return self._scoped_instances[service_type]

            # Create new instance
            self._resolution_stack.append(service_type)
            try:
                instance = self._create_instance(descriptor)

                # Store singleton/scoped instances
                if descriptor.lifetime == ServiceLifetime.SINGLETON:
                    self._singletons[service_type] = instance
                elif descriptor.lifetime == ServiceLifetime.SCOPED:
                    self._scoped_instances[service_type] = instance

                return instance

            finally:
                self._resolution_stack.pop()

    def try_resolve(self, service_type: Union[Type[T], str]) -> Optional[T]:
        """
        Try to resolve a service, returning None if not found.

        Args:
            service_type: The type of service to resolve or string name

        Returns:
            Instance of the service or None if not found
        """
        try:
            return self.resolve(service_type)
        except DependencyError:
            return None

    def _resolve_by_string(self, service_name: str) -> Any:
        """
        Resolve a service by string name.

        Args:
            service_name: String name of the service

        Returns:
            Service instance

        Raises:
            DependencyError: If service not found
        """
        # Check for string-registered services first
        for service_type, instance in self._singletons.items():
            if (
                hasattr(service_type, "__name__")
                and service_type.__name__ == service_name
            ) or service_type == service_name:
                return instance

        # Check descriptors for matching service names
        for service_type, descriptor in self._descriptors.items():
            if (
                hasattr(service_type, "__name__")
                and service_type.__name__ == service_name
            ) or service_type == service_name:
                return self.resolve(service_type)

        raise DependencyError(
            f"Service '{service_name}' not found", service_type=service_name
        )


    def is_registered(self, service_type: Type[T]) -> bool:
        """Check if a service type is registered.

        Required to satisfy the ``IServiceContainer`` ABC contract; even though
        no code path calls this method directly, removing it breaks
        instantiation of any concrete subclass.
        """
        return service_type in self._descriptors

    def clear_scoped(self) -> None:
        """Clear all scoped instances."""
        self._scoped_instances.clear()
        logger.debug("Cleared scoped service instances")


    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        Create an instance using the service descriptor.

        Args:
            descriptor: Service descriptor containing creation information

        Returns:
            Created service instance

        Raises:
            DependencyError: If instance creation fails
        """
        try:
            # Resolve dependencies
            resolved_dependencies = {}
            for param_name, dep_type in descriptor.dependencies.items():
                if isinstance(dep_type, str):
                    if dep_type == "EyemapServiceContainer":
                        resolved_dependencies[param_name] = self
                    else:
                        resolved_dependencies[param_name] = self.resolve(dep_type)
                else:
                    resolved_dependencies[param_name] = self.resolve(dep_type)

            # Create instance with resolved dependencies
            instance = descriptor.factory(**resolved_dependencies)
            logger.debug(f"Created instance of {descriptor.service_type.__name__}")
            return instance

        except Exception as e:
            raise DependencyError(
                f"Failed to create instance of {descriptor.service_type.__name__}: {str(e)}",
                service_type=descriptor.service_type.__name__,
            ) from e


class EyemapServiceContainer(VisualizationServiceContainer):
    """Specialized service container for eyemap services."""

    def __init__(self, config: Optional[EyemapConfiguration] = None):
        """
        Initialize the eyemap service container.

        Args:
            config: Optional configuration to use for service registration
        """
        super().__init__()
        self.config = config or ConfigurationManager.create_default()
        self._register_core_services()

    def _register_core_services(self) -> None:
        """Register core eyemap services with the container."""
        with ErrorContext("core_service_registration"):
            # Register configuration as singleton
            self.register_instance(EyemapConfiguration, self.config)

            # Import services locally to avoid circular dependencies
            from .color import ColorPalette, ColorMapper
            from .coordinate_system import EyemapCoordinateSystem
            from .data_processing import DataProcessor
            from .rendering import RenderingManager
            from .region_grid_processor import RegionGridProcessorFactory
            from .file_output_manager import FileOutputManagerFactory

            # Register color services
            self.register_singleton(ColorPalette, lambda: ColorPalette())
            self.register_singleton(
                ColorMapper,
                lambda color_palette: ColorMapper(color_palette),
                dependencies={"color_palette": ColorPalette},
            )

            # Register coordinate system
            self.register_singleton(
                EyemapCoordinateSystem,
                self._create_coordinate_system,
                dependencies={"config": EyemapConfiguration},
            )

            # Register data processor
            self.register_singleton(DataProcessor, lambda: DataProcessor())

            # Register rendering manager
            self.register_singleton(
                RenderingManager,
                self._create_rendering_manager,
                dependencies={
                    "config": EyemapConfiguration,
                    "color_mapper": ColorMapper,
                },
            )

            # Register factory services as singletons
            self.register_singleton(
                RegionGridProcessorFactory, lambda: RegionGridProcessorFactory()
            )
            self.register_singleton(
                FileOutputManagerFactory, lambda: FileOutputManagerFactory()
            )

            # Try to register performance services if available
            self._register_performance_services()

            # Register EyemapGenerator itself
            self._register_eyemap_generator()

    def _create_coordinate_system(
        self, config: EyemapConfiguration
    ) -> "EyemapCoordinateSystem":
        """Create coordinate system from configuration."""
        from .coordinate_system import EyemapCoordinateSystem

        coord_params = config.get_coordinate_system_params()
        return EyemapCoordinateSystem(
            hex_size=coord_params["hex_size"],
            spacing_factor=coord_params["spacing_factor"],
            margin=coord_params["margin"],
        )

    def _create_rendering_manager(
        self, config: EyemapConfiguration, color_mapper: "ColorMapper"
    ) -> "RenderingManager":
        """Create rendering manager from configuration."""
        from .rendering import RenderingManager

        rendering_config = config.to_rendering_config()
        return RenderingManager(rendering_config, color_mapper)

    def _register_performance_services(self) -> None:
        """Register performance services if available."""
        # Import performance services locally (optional dependency)
        from .performance import (
            PerformanceOptimizerFactory,
            get_performance_monitor,
            MemoryOptimizer,
        )

        self.register_singleton(MemoryOptimizer, lambda: MemoryOptimizer())
        self.register_singleton(
            PerformanceOptimizerFactory, lambda: PerformanceOptimizerFactory()
        )

        # Register performance monitor instance
        monitor = get_performance_monitor()
        self.register_instance(type(monitor), monitor)

        logger.debug("Registered performance services")

    def _register_eyemap_generator(self) -> None:
        """Register EyemapGenerator with the container."""
        # Import locally to avoid circular imports
        from .eyemap_generator import EyemapGenerator

        # Simple registration without complex dependencies
        # The EyemapGenerator will resolve its own dependencies from the container
        self.register_singleton(
            EyemapGenerator,
            lambda: EyemapGenerator(config=self.config, service_container=self),
        )
        logger.debug("Registered EyemapGenerator service")



# Global container instance for convenience
_default_container: Optional[EyemapServiceContainer] = None


def get_default_container() -> EyemapServiceContainer:
    """
    Get the default service container, creating it if necessary.

    Returns:
        Default service container instance

    Raises:
        DependencyError: If container creation fails
    """
    global _default_container
    if _default_container is None:
        try:
            _default_container = EyemapServiceContainer()
            logger.debug("Created default service container")
        except Exception as e:
            raise DependencyError(
                f"Failed to create default service container: {str(e)}"
            ) from e
    return _default_container




def reset_default_container() -> None:
    """Reset the default container to None, forcing recreation on next access."""
    global _default_container
    _default_container = None
