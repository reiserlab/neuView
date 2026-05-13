#!/usr/bin/env python3
"""
Auto-increment version script for neuview project.

This script implements a new workflow for version management:
1. Reads the current version from git tags (source of truth)
2. Increments the patch version by 1
3. Updates the version in pyproject.toml (without 'v' prefix)
4. Commits that change to the current branch
5. Creates a git tag with the v-prefixed version

The script uses GitPython exclusively for all git operations (no CLI commands), the
semver package for version parsing and incrementing, and the toml package for
pyproject.toml manipulation.

Example workflow:
  Current git tag: v2.7.4
  → Update pyproject.toml version to "2.7.5"
  → Commit: "Bump version to v2.7.5"
  → Create git tag: v2.7.5
"""

import sys
import click
import tomlkit
import yaml
import semver
from pathlib import Path
from typing import Optional
from git import Repo, InvalidGitRepositoryError, GitCommandError


def get_git_repo() -> Repo:
    """Get the git repository object."""
    try:
        # Find the git repository (searches upwards from current directory)
        repo = Repo(search_parent_directories=True)
        return repo
    except InvalidGitRepositoryError:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)


def get_latest_version() -> Optional[str]:
    """Get the latest version tag from git using GitPython."""
    try:
        repo = get_git_repo()

        # Get all tags
        tags = list(repo.tags)

        if not tags:
            print("No git tags found", file=sys.stderr)
            return None

        # Sort tags by the commit date they reference (most recent last)
        try:
            sorted_tags = sorted(
                tags, key=lambda t: t.commit.committed_datetime, reverse=True
            )
        except Exception as e:
            print(f"Error sorting tags by commit date: {e}", file=sys.stderr)
            # Fallback: sort tags alphabetically by name
            sorted_tags = sorted(tags, key=str, reverse=True)

        # Find the first tag that matches semantic versioning pattern
        for tag in sorted_tags:
            tag_name = str(tag)
            try:
                # Try to parse as semver to validate format
                version_str = tag_name.lstrip("v")
                version_parts = version_str.split(".")
                if len(version_parts) == 2:
                    version_str = f"{version_str}.0"
                elif len(version_parts) == 1:
                    version_str = f"{version_str}.0.0"

                semver.Version.parse(version_str)
                return tag_name
            except ValueError:
                continue

        print("No valid semantic version tags found", file=sys.stderr)
        return None

    except GitCommandError as e:
        print(f"Git command error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting git tags: {e}", file=sys.stderr)
        return None


def parse_version(version_tag: str) -> semver.Version:
    """Parse a version tag into a semver Version object."""
    # Remove 'v' prefix if present
    version_str = version_tag.lstrip("v")

    # Handle incomplete versions by normalizing them first
    # Convert "1.2" to "1.2.0" for proper semver parsing
    version_parts = version_str.split(".")
    if len(version_parts) == 2:
        version_str = f"{version_str}.0"
    elif len(version_parts) == 1:
        version_str = f"{version_str}.0.0"

    try:
        return semver.Version.parse(version_str)
    except ValueError as e:
        raise ValueError(f"Invalid version format: {version_tag}") from e


def get_project_root() -> Path:
    """Get the project root directory (where pyproject.toml is located)."""
    try:
        repo = get_git_repo()
        project_root = Path(repo.working_dir)
        pyproject_path = project_root / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

        return project_root
    except Exception as e:
        print(f"Error finding project root: {e}", file=sys.stderr)
        sys.exit(1)


def get_neuprint_config() -> Optional[dict]:
    """Read neuprint.server and neuprint.dataset from config.yaml at the project root."""
    try:
        project_root = get_project_root()
        config_path = project_root / "config.yaml"

        if not config_path.exists():
            print(f"Warning: {config_path} not found", file=sys.stderr)
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        neuprint = config.get("neuprint", {})
        server = neuprint.get("server")
        dataset = neuprint.get("dataset")

        if not server or not dataset:
            print(
                "Warning: neuprint.server and/or neuprint.dataset missing from config.yaml",
                file=sys.stderr,
            )
            return None

        return {"server": server, "dataset": dataset}
    except Exception as e:
        print(f"Warning: could not read neuprint config: {e}", file=sys.stderr)
        return None


def build_tag_message(tag: str, neuprint: Optional[dict]) -> str:
    """Build the annotated tag message, including neuprint info when available."""
    message = f"Release {tag}"
    if neuprint:
        message += (
            f"\n\nneuprint.server: {neuprint['server']}"
            f"\nneuprint.dataset: {neuprint['dataset']}"
        )
    return message


def update_pyproject_version(new_version_without_v: str, dry_run: bool = False) -> bool:
    """Update the version in pyproject.toml using tomlkit (preserves formatting/comments)."""
    try:
        project_root = get_project_root()
        pyproject_path = project_root / "pyproject.toml"

        # Read the current pyproject.toml
        with open(pyproject_path, "r", encoding="utf-8") as f:
            pyproject_data = tomlkit.parse(f.read())

        # Get current version for comparison
        current_version = pyproject_data.get("project", {}).get("version", "unknown")
        print(f"Current pyproject.toml version: {current_version}")
        print(f"New pyproject.toml version: {new_version_without_v}")

        if dry_run:
            print(
                f"[DRY RUN] Would update pyproject.toml version to: {new_version_without_v}"
            )
            return True

        # Update the version
        if "project" not in pyproject_data:
            pyproject_data["project"] = tomlkit.table()
        pyproject_data["project"]["version"] = new_version_without_v

        # Write back to file
        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(pyproject_data))

        print(
            f"Successfully updated pyproject.toml version to: {new_version_without_v}"
        )
        return True

    except Exception as e:
        print(f"Error updating pyproject.toml: {e}", file=sys.stderr)
        return False


def commit_version_change(new_version_with_v: str, dry_run: bool = False) -> bool:
    """Commit the version change to git using GitPython."""
    try:
        repo = get_git_repo()

        # Add pyproject.toml to staging
        try:
            repo.index.add(["pyproject.toml"])
        except Exception as e:
            print(f"Error adding pyproject.toml to git: {e}", file=sys.stderr)
            return False

        # Check if there are changes to commit
        if not repo.index.diff("HEAD"):
            print("No changes to commit in pyproject.toml")
            return True

        if dry_run:
            print(
                f"[DRY RUN] Would commit version change with message: 'Bump version to {new_version_with_v}'"
            )
            return True

        # Commit the changes
        commit_message = f"Bump version to {new_version_with_v}"
        try:
            repo.index.commit(commit_message)
            print(f"Successfully committed version change: {commit_message}")
            return True
        except Exception as e:
            print(f"Error committing version change: {e}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error in git commit operation: {e}", file=sys.stderr)
        return False


def create_git_tag(tag: str, message: str, dry_run: bool = False) -> bool:
    """Create a new annotated git tag using GitPython."""
    try:
        repo = get_git_repo()

        # Check if the tag already exists
        existing_tags = [str(t) for t in repo.tags]
        if tag in existing_tags:
            print(f"Tag {tag} already exists, skipping creation", file=sys.stderr)
            return False

        if dry_run:
            print(f"[DRY RUN] Would create git tag: {tag}")
            print(f"[DRY RUN] Tag message:\n{message}")
            return True

        # Create the tag
        try:
            repo.create_tag(tag, message=message)
            print(f"Successfully created git tag: {tag}")
            return True
        except Exception as e:
            print(f"Error creating git tag: {e}", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error in git tag operation: {e}", file=sys.stderr)
        return False


@click.command(
    help="Increment version, update pyproject.toml, commit, and create git tag"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making actual changes",
)
def main(dry_run: bool):
    """Main function to increment version, update pyproject.toml, commit, and create tag."""
    if dry_run:
        print("Starting version increment process (DRY RUN MODE)...")
    else:
        print("Starting version increment process...")

    # Get the latest version
    latest_version = get_latest_version()
    if not latest_version:
        print("Could not determine latest version", file=sys.stderr)
        sys.exit(1)

    print(f"Current latest git tag: {latest_version}")

    try:
        # Parse the version
        parsed_version = parse_version(latest_version)
        print(
            f"Parsed version: major={parsed_version.major}, minor={parsed_version.minor}, patch={parsed_version.patch}"
        )

        # Increment patch version
        incremented_version = parsed_version.bump_patch()
        new_version_with_v = f"v{incremented_version}"
        new_version_without_v = str(incremented_version)

        print(f"New version (for git tag): {new_version_with_v}")
        print(f"New version (for pyproject.toml): {new_version_without_v}")

        # Step 1: Update pyproject.toml
        if not update_pyproject_version(new_version_without_v, dry_run=dry_run):
            print("Failed to update pyproject.toml", file=sys.stderr)
            sys.exit(1)

        # Step 2: Commit the change
        if not commit_version_change(new_version_with_v, dry_run=dry_run):
            print("Failed to commit version change", file=sys.stderr)
            sys.exit(1)

        # Step 3: Create the git tag (with neuprint info from config.yaml)
        neuprint_config = get_neuprint_config()
        tag_message = build_tag_message(new_version_with_v, neuprint_config)
        if not create_git_tag(new_version_with_v, tag_message, dry_run=dry_run):
            print("Failed to create git tag", file=sys.stderr)
            sys.exit(1)

        if dry_run:
            print(f"\n[DRY RUN] Summary of what would be done:")
            print(f"  1. Update pyproject.toml version: {new_version_without_v}")
            print(
                f"  2. Commit change with message: 'Bump version to {new_version_with_v}'"
            )
            print(f"  3. Create git tag: {new_version_with_v}")
            print(f"\nTo actually perform these actions, run without --dry-run")
        else:
            print(
                f"\n✓ Successfully incremented version from {latest_version} to {new_version_with_v}"
            )
            print(f"  • Updated pyproject.toml to version {new_version_without_v}")
            print(f"  • Committed the change")
            print(f"  • Created git tag {new_version_with_v}")
            print(f"\nNext steps (optional):")
            print(f"  • Push commits: git push")
            print(f"  • Push tag: git push origin {new_version_with_v}")

    except ValueError as e:
        print(f"Error parsing version: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
