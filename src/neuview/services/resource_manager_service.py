"""
Resource Manager Service for neuView.

This service handles resource management logic that was previously part of the
PageGenerator class. It provides methods for copying static files, managing
directories, and handling other file system operations.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import get_project_root, get_static_dir, get_templates_dir
from .neuroglancer_js_service import NeuroglancerJSService

logger = logging.getLogger(__name__)


class ResourceManagerService:
    """Service for managing static files, directories, and other resources."""

    def __init__(self, config, output_dir: Path, jinja_env=None):
        """Initialize the resource manager service.

        Args:
            config: Configuration object containing settings
            output_dir: Base output directory path
            jinja_env: Jinja2 environment for template rendering
        """
        self.config = config
        self.output_dir = output_dir
        self._jinja_env = jinja_env
        self._neuroglancer_js_service = None
        # Use built-in template directory
        self.template_dir = get_templates_dir()

    @property
    def neuroglancer_js_service(self):
        """Lazy property to create neuroglancer JS service when needed."""
        if self._neuroglancer_js_service is None and self._jinja_env is not None:
            self._neuroglancer_js_service = NeuroglancerJSService(
                self.config, self._jinja_env
            )
            logger.debug("Neuroglancer JS service created lazily")
        return self._neuroglancer_js_service

    @neuroglancer_js_service.setter
    def neuroglancer_js_service(self, value):
        """Setter for neuroglancer JS service property."""
        self._neuroglancer_js_service = value

    def update_template_environment(self, jinja_env):
        """Update the neuroglancer JS service with a new template environment.

        Args:
            jinja_env: Jinja2 environment for template rendering
        """
        self._jinja_env = jinja_env
        self._neuroglancer_js_service = (
            None  # Reset to force recreation with new environment
        )
        logger.debug(
            "Template environment updated, neuroglancer JS service will be recreated"
        )

    def setup_output_directories(self) -> Dict[str, Path]:
        """
        Create and set up all required output directories.

        Returns:
            Dictionary mapping directory names to their paths
        """
        directories = {}

        # Create main output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        directories["output"] = self.output_dir

        # Create types subdirectory for neuron type pages
        types_dir = self.output_dir / "types"
        types_dir.mkdir(parents=True, exist_ok=True)
        directories["types"] = types_dir

        # Create eyemaps directory for hexagon grid images
        eyemaps_dir = self.output_dir / "eyemaps"
        eyemaps_dir.mkdir(parents=True, exist_ok=True)
        directories["eyemaps"] = eyemaps_dir

        # Create static directory for CSS, JS, and other assets
        static_dir = self.output_dir / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        directories["static"] = static_dir

        # Create subdirectories within static
        css_dir = static_dir / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
        directories["css"] = css_dir

        js_dir = static_dir / "js"
        js_dir.mkdir(parents=True, exist_ok=True)
        directories["js"] = js_dir

        # Create cache directory for temporary files
        cache_dir = self.output_dir / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        directories["cache"] = cache_dir

        logger.info(f"Set up output directories: {list(directories.keys())}")
        return directories

    def copy_static_files(self, mode: str = "check_exists") -> bool:
        """
        Copy static files and directories to the output directory.

        This includes:
        - CSS files from static/css/
        - JS files from static/js/ (with selective copying)
        - Generated neuroglancer-url-generator.js
        - Images and other assets from static/images/ and other subdirectories
        - LICENSE file from static/
        - Template static assets from templates/static/

        Args:
            mode: Copy behavior mode:
                - "check_exists": Only copy files if they don't exist (default for pop)
                - "force_all": Force copy/regenerate all files (for generate command)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the static files directory
            static_source_dir = get_static_dir()

            if not static_source_dir.exists():
                logger.warning(
                    f"Static source directory not found: {static_source_dir}"
                )
                return False

            # Set up output directories
            directories = self.setup_output_directories()
            output_static_dir = directories["static"]

            force_copy = mode == "force_all"

            # Copy CSS files
            css_source_dir = static_source_dir / "css"
            if css_source_dir.exists():
                output_css_dir = directories["css"]
                if force_copy or self._should_copy_files(
                    css_source_dir, output_css_dir, "*.css"
                ):
                    logger.debug("Copying CSS files")
                    self._copy_files_recursive(
                        css_source_dir, output_css_dir, "*.css", force_copy
                    )
                else:
                    logger.debug("CSS files already exist, skipping copy")

            # Copy JS files (excluding neuroglancer-url-generator.js which is generated dynamically)
            js_source_dir = static_source_dir / "js"
            if js_source_dir.exists():
                output_js_dir = directories["js"]
                if force_copy or self._should_copy_js_files(
                    js_source_dir, output_js_dir
                ):
                    logger.debug("Copying JS files")
                    self._copy_js_files_selective(
                        js_source_dir, output_js_dir, force_copy
                    )
                else:
                    logger.debug("JS files already exist, skipping copy")

            # Generate neuroglancer JavaScript file with dynamic template selection
            generated_file = output_js_dir / "neuroglancer-url-generator.js"
            if force_copy or not generated_file.exists():
                logger.debug(
                    f"Neuroglancer JS service available: {self.neuroglancer_js_service is not None}"
                )
                if not self.neuroglancer_js_service:
                    logger.error(
                        "No Jinja environment available - neuroglancer JS service is required"
                    )
                    return False

                logger.debug("Attempting to generate neuroglancer JavaScript file")
                success = self.neuroglancer_js_service.generate_neuroglancer_js(
                    self.output_dir
                )
                logger.debug(f"Neuroglancer JS generation result: {success}")

                if not success:
                    logger.error(
                        "Failed to generate neuroglancer JavaScript file - this is a critical error"
                    )
                    return False

                # Verify the generated file exists and contains expected content
                if not generated_file.exists():
                    logger.error(
                        "Neuroglancer JavaScript file does not exist after generation"
                    )
                    return False

                with open(generated_file, "r") as f:
                    content = f.read()
                newline = "\n"
                logger.debug(
                    f"Generated file exists, size: {len(content)} chars, lines: {len(content.split(newline))}"
                )

                if "function initializeNeuroglancerLinks" not in content:
                    logger.error(
                        "Generated neuroglancer JavaScript file is missing required function 'initializeNeuroglancerLinks'"
                    )
                    return False

                logger.debug("✓ Neuroglancer JavaScript file generated successfully")
            else:
                logger.debug(
                    "Neuroglancer JavaScript file already exists, skipping generation"
                )

            # Copy other static assets (images, fonts, etc.) - Enhanced version
            # Copy all directories and files not already handled
            excluded_dirs = {"css", "js"}  # Already handled above
            for item in static_source_dir.iterdir():
                if item.is_file():
                    # Handle LICENSE file specially - copy to root output directory
                    if item.name == "LICENSE":
                        dest_file = Path(self.output_dir) / item.name
                        if force_copy or not dest_file.exists():
                            shutil.copy2(item, dest_file)
                            logger.debug(f"Copied LICENSE file to root: {item.name}")
                        else:
                            logger.debug(
                                f"LICENSE file already exists in root, skipping: {item.name}"
                            )
                    # Copy other individual files (images, fonts, etc.) to static directory
                    elif item.suffix.lower() in [
                        ".ico",
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".svg",
                        ".webp",
                        ".ttf",
                        ".woff",
                        ".woff2",
                        ".eot",
                        ".otf",
                    ]:
                        dest_file = output_static_dir / item.name
                        if force_copy or not dest_file.exists():
                            shutil.copy2(item, dest_file)
                            logger.debug(f"Copied static file: {item.name}")
                        else:
                            logger.debug(
                                f"Static file already exists, skipping: {item.name}"
                            )
                elif item.is_dir() and item.name not in excluded_dirs:
                    # Recursively copy entire directories (like images/)
                    dest_subdir = output_static_dir / item.name
                    if force_copy or self._should_copy_files(item, dest_subdir, "*"):
                        dest_subdir.mkdir(parents=True, exist_ok=True)
                        self._copy_files_recursive(item, dest_subdir, "*", force_copy)
                        logger.debug(f"Copied static directory: {item.name}")
                    else:
                        logger.debug(
                            f"Static directory already exists, skipping: {item.name}"
                        )

            # Also copy template static assets (like templates/static/img/)
            template_static_dir = get_project_root() / "templates" / "static"
            if template_static_dir.exists():
                logger.debug(f"Found template static directory: {template_static_dir}")
                # Copy template static assets to output
                for item in template_static_dir.iterdir():
                    if item.is_dir():
                        # Copy directories like img/
                        dest_subdir = output_static_dir / item.name
                        if force_copy or self._should_copy_files(
                            item, dest_subdir, "*"
                        ):
                            dest_subdir.mkdir(parents=True, exist_ok=True)
                            self._copy_files_recursive(
                                item, dest_subdir, "*", force_copy
                            )
                            logger.debug(
                                f"Copied template static directory: {item.name}"
                            )
                        else:
                            logger.debug(
                                f"Template static directory already exists, skipping: {item.name}"
                            )
                    elif item.is_file():
                        # Copy individual template static files
                        dest_file = output_static_dir / item.name
                        if force_copy or not dest_file.exists():
                            shutil.copy2(item, dest_file)
                            logger.debug(f"Copied template static file: {item.name}")
                        else:
                            logger.debug(
                                f"Template static file already exists, skipping: {item.name}"
                            )

            logger.info("Successfully copied static files to output directory")
            return True

        except Exception as e:
            logger.error(f"Failed to copy static files: {e}")
            return False

    def verify_static_content(self) -> Dict[str, bool]:
        """
        Verify that all expected static content has been copied to output.

        Returns:
            Dictionary with verification results
        """
        results = {}
        directories = self.setup_output_directories()
        output_static_dir = directories["static"]

        # Check for essential directories
        essential_dirs = ["css", "js", "images"]
        for dir_name in essential_dirs:
            dir_path = output_static_dir / dir_name
            results[f"dir_{dir_name}"] = dir_path.exists()
            if dir_path.exists():
                file_count = len(list(dir_path.rglob("*")))
                results[f"dir_{dir_name}_files"] = file_count

        # Check for essential files
        essential_files = [
            "css/neuron-page.css",
            "js/jquery-3.7.1.min.js",
            "js/neuron-page.js",
            "js/neuroglancer-url-generator.js",
        ]

        for file_path in essential_files:
            full_path = output_static_dir / file_path
            results[f"file_{file_path.replace('/', '_')}"] = full_path.exists()

        return results

    def _copy_js_files_selective(
        self, source_dir: Path, dest_dir: Path, force_copy: bool = False
    ) -> None:
        """
        Copy JavaScript files selectively, excluding neuroglancer-url-generator.js.

        Args:
            source_dir: Source directory containing JS files
            dest_dir: Destination directory for JS files
            force_copy: If True, copy files even if they already exist
        """
        try:
            for js_file in source_dir.glob("*.js"):
                # Skip neuroglancer-url-generator.js as it's generated dynamically
                if js_file.name == "neuroglancer-url-generator.js":
                    logger.debug(
                        f"Skipping static {js_file.name} (will be generated dynamically)"
                    )
                    continue

                dest_file = dest_dir / js_file.name
                if force_copy or not dest_file.exists():
                    shutil.copy2(js_file, dest_file)
                    logger.debug(f"Copied JS file: {js_file.name}")
                else:
                    logger.debug(f"JS file already exists, skipping: {js_file.name}")

        except Exception as e:
            logger.error(f"Failed to copy JS files selectively: {e}")
            raise

    def _copy_files_recursive(
        self,
        source_dir: Path,
        dest_dir: Path,
        pattern: str = "*",
        force_copy: bool = False,
    ) -> None:
        """
        Recursively copy files matching a pattern from source to destination.

        Args:
            source_dir: Source directory
            dest_dir: Destination directory
            pattern: File pattern to match (e.g., '*.css', '*.js')
            force_copy: If True, copy files even if they already exist
        """
        try:
            for item in source_dir.rglob(pattern):
                if item.is_file():
                    # Maintain directory structure
                    relative_path = item.relative_to(source_dir)
                    dest_path = dest_dir / relative_path
                    if force_copy or not dest_path.exists():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)
                        logger.debug(f"Copied {item} to {dest_path}")
                    else:
                        logger.debug(f"File already exists, skipping: {dest_path}")
        except Exception as e:
            logger.error(f"Failed to copy files from {source_dir} to {dest_dir}: {e}")
            raise

    def _should_copy_files(
        self, source_dir: Path, dest_dir: Path, pattern: str = "*"
    ) -> bool:
        """
        Check if files matching a pattern should be copied based on existence in destination.

        Args:
            source_dir: Source directory
            dest_dir: Destination directory
            pattern: File pattern to match (e.g., '*.css', '*.js')

        Returns:
            True if any files need to be copied, False if all already exist
        """
        try:
            # If destination directory doesn't exist, we need to copy
            if not dest_dir.exists():
                return True

            # Check if any source files are missing in destination
            for item in source_dir.rglob(pattern):
                if item.is_file():
                    relative_path = item.relative_to(source_dir)
                    dest_path = dest_dir / relative_path
                    if not dest_path.exists():
                        return True

            # All files already exist
            return False
        except Exception as e:
            logger.debug(f"Error checking file existence, will copy: {e}")
            return True

    def _should_copy_js_files(self, source_dir: Path, dest_dir: Path) -> bool:
        """
        Check if JS files should be copied (excluding neuroglancer-url-generator.js).

        Args:
            source_dir: Source directory containing JS files
            dest_dir: Destination directory for JS files

        Returns:
            True if any JS files need to be copied, False if all already exist
        """
        try:
            # If destination directory doesn't exist, we need to copy
            if not dest_dir.exists():
                return True

            # Check if any JS files (except neuroglancer-url-generator.js) are missing
            for js_file in source_dir.glob("*.js"):
                if js_file.name == "neuroglancer-url-generator.js":
                    continue  # Skip this as it's generated dynamically

                dest_file = dest_dir / js_file.name
                if not dest_file.exists():
                    return True

            # All JS files already exist
            return False
        except Exception as e:
            logger.debug(f"Error checking JS file existence, will copy: {e}")
            return True

    def check_static_files_exist(self) -> Dict[str, bool]:
        """
        Check if essential static files already exist in the output directory.

        Returns:
            Dictionary mapping file categories to their existence status
        """
        try:
            directories = self.setup_output_directories()
            output_static_dir = directories["static"]
            output_css_dir = directories["css"]
            output_js_dir = directories["js"]

            results = {
                "css_dir": output_css_dir.exists(),
                "js_dir": output_js_dir.exists(),
                "neuroglancer_js": (
                    output_js_dir / "neuroglancer-url-generator.js"
                ).exists(),
                "essential_css": (output_css_dir / "neuron-page.css").exists(),
                "essential_js": all(
                    [
                        (output_js_dir / "jquery-3.7.1.min.js").exists(),
                        (output_js_dir / "neuron-page.js").exists(),
                    ]
                ),
                "images_dir": (output_static_dir / "images").exists(),
            }

            return results
        except Exception as e:
            logger.error(f"Error checking static files existence: {e}")
            return {}

    def clean_dynamic_files(
        self, neuron_type: str = None, soma_side: str = None
    ) -> bool:
        """
        Clean dynamic files that should be regenerated (HTML pages and eyemaps).

        Args:
            neuron_type: If specified, only clean files for this neuron type
            soma_side: If specified, only clean files for this soma side

        Returns:
            True if successful, False otherwise
        """
        try:
            directories = self.setup_output_directories()

            # Clean HTML pages in types directory
            types_dir = directories["types"]
            if types_dir.exists():
                if neuron_type and soma_side:
                    # Clean specific neuron type and soma side
                    html_file = types_dir / f"{neuron_type}_{soma_side}.html"
                    if html_file.exists():
                        html_file.unlink()
                        logger.debug(f"Removed HTML file: {html_file.name}")
                elif neuron_type:
                    # Clean all soma sides for this neuron type
                    for html_file in types_dir.glob(f"{neuron_type}_*.html"):
                        html_file.unlink()
                        logger.debug(f"Removed HTML file: {html_file.name}")
                else:
                    # Clean all HTML files
                    for html_file in types_dir.glob("*.html"):
                        html_file.unlink()
                        logger.debug(f"Removed HTML file: {html_file.name}")

            # Clean eyemap images
            eyemaps_dir = directories["eyemaps"]
            if eyemaps_dir.exists():
                if neuron_type and soma_side:
                    # Clean specific neuron type and soma side eyemaps
                    for eyemap_file in eyemaps_dir.glob(f"{neuron_type}_{soma_side}_*"):
                        eyemap_file.unlink()
                        logger.debug(f"Removed eyemap file: {eyemap_file.name}")
                elif neuron_type:
                    # Clean all soma sides for this neuron type
                    for eyemap_file in eyemaps_dir.glob(f"{neuron_type}_*"):
                        eyemap_file.unlink()
                        logger.debug(f"Removed eyemap file: {eyemap_file.name}")
                else:
                    # Clean all eyemap files
                    for eyemap_file in eyemaps_dir.glob("*"):
                        if eyemap_file.is_file():
                            eyemap_file.unlink()
                            logger.debug(f"Removed eyemap file: {eyemap_file.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to clean dynamic files: {e}")
            return False

    def copy_template_files(self, template_names: Optional[List[str]] = None) -> bool:
        """
        Copy template files to the output directory.

        Args:
            template_names: Optional list of specific template names to copy.
                          If None, copies all templates.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.template_dir.exists():
                logger.warning(f"Template directory not found: {self.template_dir}")
                return False

            output_templates_dir = self.output_dir / "templates"
            output_templates_dir.mkdir(parents=True, exist_ok=True)

            if template_names:
                # Copy specific templates
                for template_name in template_names:
                    template_path = self.template_dir / template_name
                    if template_path.exists():
                        shutil.copy2(
                            template_path, output_templates_dir / template_name
                        )
                        logger.debug(f"Copied template {template_name}")
                    else:
                        logger.warning(f"Template not found: {template_path}")
            else:
                # Copy all templates
                self._copy_files_recursive(
                    self.template_dir, output_templates_dir, "*.html"
                )
                self._copy_files_recursive(
                    self.template_dir, output_templates_dir, "*.jinja"
                )
                self._copy_files_recursive(
                    self.template_dir, output_templates_dir, "*.j2"
                )

            logger.info("Successfully copied template files")
            return True

        except Exception as e:
            logger.error(f"Failed to copy template files: {e}")
            return False

    def clean_output_directory(self, preserve_cache: bool = True) -> bool:
        """
        Clean the output directory, optionally preserving cache.

        Args:
            preserve_cache: If True, preserves the .cache directory

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.output_dir.exists():
                logger.info("Output directory does not exist, nothing to clean")
                return True

            cache_dir = self.output_dir / ".cache"
            cache_contents = []

            # Back up cache if preserving
            if preserve_cache and cache_dir.exists():
                import tempfile

                temp_cache = Path(tempfile.mkdtemp())
                shutil.copytree(cache_dir, temp_cache / ".cache")
                cache_contents = list((temp_cache / ".cache").rglob("*"))

            # Remove output directory
            shutil.rmtree(self.output_dir)

            # Recreate directories
            self.setup_output_directories()

            # Restore cache if it was preserved
            if preserve_cache and cache_contents:
                temp_cache_dir = cache_contents[0].parent if cache_contents else None
                if temp_cache_dir and temp_cache_dir.exists():
                    shutil.copytree(temp_cache_dir, cache_dir, dirs_exist_ok=True)
                    shutil.rmtree(temp_cache_dir.parent)

            logger.info(f"Cleaned output directory: {self.output_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to clean output directory: {e}")
            return False

    def ensure_directory_exists(self, directory_path: Path) -> bool:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            directory_path: Path to the directory

        Returns:
            True if directory exists or was created successfully
        """
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory_path}: {e}")
            return False

    def get_file_size(self, file_path: Path) -> Optional[int]:
        """
        Get the size of a file in bytes.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes, or None if file doesn't exist or error occurs
        """
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.stat().st_size
            return None
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {e}")
            return None

    def list_directory_contents(
        self, directory_path: Path, pattern: str = "*", recursive: bool = False
    ) -> List[Path]:
        """
        List contents of a directory with optional pattern matching.

        Args:
            directory_path: Path to the directory
            pattern: File pattern to match (default: '*' for all files)
            recursive: If True, search recursively

        Returns:
            List of matching file paths
        """
        try:
            if not directory_path.exists() or not directory_path.is_dir():
                return []

            if recursive:
                return list(directory_path.rglob(pattern))
            else:
                return list(directory_path.glob(pattern))

        except Exception as e:
            logger.error(f"Failed to list directory contents for {directory_path}: {e}")
            return []

    def copy_file(
        self, source_path: Path, dest_path: Path, create_dirs: bool = True
    ) -> bool:
        """
        Copy a single file from source to destination.

        Args:
            source_path: Source file path
            dest_path: Destination file path
            create_dirs: If True, create destination directories if they don't exist

        Returns:
            True if successful, False otherwise
        """
        try:
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False

            if create_dirs:
                dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_path, dest_path)
            logger.debug(f"Copied {source_path} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy {source_path} to {dest_path}: {e}")
            return False

    def move_file(
        self, source_path: Path, dest_path: Path, create_dirs: bool = True
    ) -> bool:
        """
        Move a file from source to destination.

        Args:
            source_path: Source file path
            dest_path: Destination file path
            create_dirs: If True, create destination directories if they don't exist

        Returns:
            True if successful, False otherwise
        """
        try:
            if not source_path.exists():
                logger.error(f"Source file does not exist: {source_path}")
                return False

            if create_dirs:
                dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(source_path), str(dest_path))
            logger.debug(f"Moved {source_path} to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to move {source_path} to {dest_path}: {e}")
            return False

    def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to the file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                logger.debug(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get statistics about managed resources.

        Returns:
            Dictionary containing resource statistics
        """
        try:
            stats = {
                "output_dir": str(self.output_dir),
                "output_dir_exists": self.output_dir.exists(),
                "template_dir": str(self.template_dir),
                "template_dir_exists": self.template_dir.exists(),
                "directories": {},
                "file_counts": {},
            }

            if self.output_dir.exists():
                # Get directory information
                for subdir in ["types", "eyemaps", "static", ".cache"]:
                    dir_path = self.output_dir / subdir
                    stats["directories"][subdir] = {
                        "exists": dir_path.exists(),
                        "path": str(dir_path),
                    }
                    if dir_path.exists():
                        files = self.list_directory_contents(dir_path, recursive=True)
                        stats["file_counts"][subdir] = len(
                            [f for f in files if f.is_file()]
                        )

            return stats

        except Exception as e:
            logger.error(f"Failed to get resource stats: {e}")
            return {"error": str(e)}
