#!/usr/bin/env python3
"""
Extract neuron types from config files and run fill-queue commands.

Usage:
    python scripts/extract_and_fill.py [config_file] [subset_category]
"""

import yaml
import sys
import subprocess
import click


def load_config(config_path: str) -> dict:
    """Load YAML config file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML file: {e}")
        sys.exit(1)


def extract_neuron_types(config: dict, subset_category: str) -> list:
    """Extract neuron types from config for given subset category."""
    subsets = config.get("subsets", {})

    if not subsets:
        print(f"❌ No 'subsets' section found in config")
        return []

    neuron_types = subsets.get(subset_category, [])

    if not neuron_types:
        available_categories = list(subsets.keys())
        print(f"❌ No neuron types found for category '{subset_category}'")
        if available_categories:
            print(f"Available categories: {', '.join(available_categories)}")
        return []

    return neuron_types


def run_fill_queue(neuron_type: str, config_file: str) -> bool:
    """Run neuview fill-queue command for a neuron type."""
    try:
        cmd = ["neuview", "fill-queue", "-n", neuron_type]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to process {neuron_type}: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("❌ 'neuview' command not found. Make sure it's installed and in PATH.")
        return False


@click.command(help="Extract neuron types from config and run fill-queue")
@click.argument(
    "config_file",
    default="config.yaml",
    type=click.Path(exists=True, dir_okay=False),
)
@click.argument(
    "subset_category",
    default="subset-medium",
)
def main(config_file: str, subset_category: str):
    # Load config
    config = load_config(config_file)

    # Extract neuron types
    neuron_types = extract_neuron_types(config, subset_category)

    if not neuron_types:
        sys.exit(1)

    print(
        f"📋 Found {len(neuron_types)} neuron types for '{subset_category}' in {config_file}"
    )

    # Show what will be processed
    for nt in neuron_types:
        print(f"  - {nt}")

    print(f"\n🚀 Processing neuron types...")

    success_count = 0
    for nt in neuron_types:
        if run_fill_queue(nt, config_file):
            print(f"✅ Processed: {nt}")
            success_count += 1
        # Error message is already printed in run_fill_queue

    print(
        f"\n🎉 Completed! Successfully processed {success_count}/{len(neuron_types)} neuron types"
    )

    if success_count < len(neuron_types):
        sys.exit(1)


if __name__ == "__main__":
    main()
