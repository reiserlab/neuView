"""
Queue File Manager for neuView.

This service handles queue file creation and management operations
that were previously part of the QueueService.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json
import yaml
from typing import List

from filelock import FileLock

from ..result import Result, Ok, Err
from ..commands import FillQueueCommand
from ..models import NeuronTypeName
from ..utils import atomic_write

logger = logging.getLogger(__name__)

# Generous timeout for the manifest critical section. The work inside is a
# small JSON rewrite that should complete in milliseconds; if we ever block
# for this long, something is genuinely wrong.
_MANIFEST_LOCK_TIMEOUT = 60


class QueueFileManager:
    """Service for handling queue file creation and management."""

    def __init__(self, config):
        """Initialize queue file manager.

        Args:
            config: Configuration object
        """
        self.config = config

    async def create_single_queue_file(
        self, command: FillQueueCommand
    ) -> Result[str, str]:
        """Create a single queue file for a specific neuron type."""
        if command.neuron_type is None:
            return Err("Neuron type is required for single queue file creation")

        # Import PageGenerator for static filename generation
        from ..page_generator import PageGenerator

        # Use "all" as default since we always generate all available pages
        soma_side_str = "all"

        # Generate HTML filename to check if it already exists
        html_filename = PageGenerator.generate_filename(
            command.neuron_type.value, soma_side_str
        )

        # Create YAML filename by replacing .html with .yaml
        yaml_filename = html_filename.replace(".html", ".yaml")

        # Create the queue directory if it doesn't exist
        queue_dir = Path(self.config.output.directory) / ".queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Full path to the YAML file
        yaml_path = queue_dir / yaml_filename

        # Prepare the generate command options
        queue_data = {
            "command": "generate",
            "config_file": command.config_file,
            "options": {
                "neuron-type": command.neuron_type.value,
                "output-dir": command.output_directory,
                "image-format": command.image_format,
                "embed": command.embed_images,
            },
            "created_at": (command.requested_at or datetime.now()).isoformat(),
        }

        # Remove None values to keep the YAML clean
        queue_data["options"] = {
            k: v for k, v in queue_data["options"].items() if v is not None
        }

        # Remove config_file if None
        if queue_data["config_file"] is None:
            del queue_data["config_file"]

        # Write the YAML file
        with open(yaml_path, "w") as f:
            yaml.dump(queue_data, f, default_flow_style=False, indent=2)

        return Ok(str(yaml_path))

    async def create_batch_queue_files(
        self, command: FillQueueCommand, neuron_types: List[str]
    ) -> Result[str, str]:
        """Create queue files for multiple neuron types."""
        # Create queue files for each type (optimized concurrent batch processing)
        created_files = []

        # Create queue directory once
        queue_dir = Path(self.config.output.directory) / ".queue"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create all commands for concurrent processing
        batch_commands = []
        for type_name in neuron_types:
            # Create a command for this specific type
            single_command = FillQueueCommand(
                neuron_type=NeuronTypeName(type_name),
                output_directory=command.output_directory,
                image_format=command.image_format,
                embed_images=command.embed_images,
                config_file=command.config_file,
                requested_at=command.requested_at,
            )
            batch_commands.append(single_command)

        # Process all commands concurrently with limited concurrency
        semaphore = asyncio.Semaphore(100)  # Limit concurrent file operations

        async def process_single_command(cmd):
            async with semaphore:
                return await self._create_single_queue_file_batch(cmd, queue_dir)

        results = await asyncio.gather(
            *[process_single_command(cmd) for cmd in batch_commands],
            return_exceptions=True,
        )

        # Collect successful results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Failed to create queue file for {batch_commands[i].neuron_type}: {result}"
                )
            elif result.is_ok():
                created_files.append(batch_commands[i].neuron_type.value)
            else:
                logger.warning(
                    f"Failed to create queue file for {batch_commands[i].neuron_type}: {result.unwrap_err()}"
                )

        if created_files:
            return Ok(f"Created {len(created_files)} queue files")
        else:
            return Err("Failed to create any queue files")

    async def _create_single_queue_file_batch(
        self, command: FillQueueCommand, queue_dir: Path
    ) -> Result[str, str]:
        """Create a single queue file for batch processing (no manifest update)."""
        if command.neuron_type is None:
            return Err("Neuron type is required for single queue file creation")

        # Import PageGenerator for static filename generation
        from ..page_generator import PageGenerator

        # Use "all" as default since we always generate all available pages
        soma_side_str = "all"

        # Generate HTML filename to check if it already exists
        html_filename = PageGenerator.generate_filename(
            command.neuron_type.value, soma_side_str
        )

        # Create YAML filename by replacing .html with .yaml
        yaml_filename = html_filename.replace(".html", ".yaml")

        # Full path to the YAML file (use pre-created queue_dir)
        yaml_path = queue_dir / yaml_filename

        # Prepare the generate command options
        queue_data = {
            "command": "generate",
            "config_file": command.config_file,
            "options": {
                "neuron-type": command.neuron_type.value,
                "output-dir": command.output_directory,
                "image-format": command.image_format,
                "embed": command.embed_images,
            },
            "created_at": (command.requested_at or datetime.now()).isoformat(),
        }

        # Remove None values to keep the YAML clean
        queue_data["options"] = {
            k: v for k, v in queue_data["options"].items() if v is not None
        }

        # Remove config_file if None
        if queue_data["config_file"] is None:
            del queue_data["config_file"]

        # Write the YAML file synchronously (no manifest update in batch mode)
        try:
            with open(yaml_path, "w") as f:
                yaml.dump(queue_data, f, default_flow_style=False, indent=2)
        except Exception as e:
            return Err(f"Failed to write queue file {yaml_path}: {str(e)}")

        return Ok(str(yaml_path))

    async def update_cache_manifest(self, neuron_types: List[str]):
        """Update the central manifest.json file with cached neuron types.

        Concurrent neuview processes (e.g. from parallel `pop-all`) all
        read-modify-write this file. A cross-process file lock serialises the
        critical section so no update is lost; the write itself is atomic so
        readers (load_cached_neuron_types) never see a partial file even
        though they don't take the lock.
        """
        cache_dir = Path(self.config.output.directory) / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_manifest_path = cache_dir / "manifest.json"
        lock_path = cache_manifest_path.with_suffix(".json.lock")

        with FileLock(str(lock_path), timeout=_MANIFEST_LOCK_TIMEOUT):
            # Load existing cache manifest or create new one
            if cache_manifest_path.exists():
                with open(cache_manifest_path, "r") as f:
                    manifest_data = json.load(f)
            else:
                manifest_data = {}

            # Get existing neuron types or initialize empty list
            existing_types = set(manifest_data.get("neuron_types", []))

            # Add new neuron types (batch update)
            existing_types.update(neuron_types)

            # Update manifest data
            manifest_data.update(
                {
                    "neuron_types": sorted(list(existing_types)),
                    "updated_at": datetime.now().isoformat(),
                    "count": len(existing_types),
                }
            )

            # Create created_at if it doesn't exist
            if "created_at" not in manifest_data:
                manifest_data["created_at"] = datetime.now().isoformat()

            # Atomic write inside the lock so non-locking readers also see
            # only fully-written manifests.
            with atomic_write(cache_manifest_path) as f:
                json.dump(manifest_data, f, indent=2, sort_keys=True)

    def load_cached_neuron_types(self) -> List[str]:
        """Load cached neuron types from the cache manifest file."""
        cache_dir = Path(self.config.output.directory) / ".cache"
        cache_manifest_path = cache_dir / "manifest.json"

        if not cache_manifest_path.exists():
            logger.debug("Cache manifest file does not exist")
            return []

        try:
            logger.debug(f"Loading cached types from {cache_manifest_path}")
            with open(cache_manifest_path, "r") as f:
                manifest_data = json.load(f)

            neuron_types = manifest_data.get("neuron_types", [])
            logger.debug(f"Loaded {len(neuron_types)} cached neuron types")
            return neuron_types

        except Exception as e:
            logger.warning(f"Failed to load cached types: {e}")
            return []
