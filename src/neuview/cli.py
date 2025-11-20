"""
Simplified CLI for neuView with clean architecture.

This CLI preserves all existing commands and options while using a simplified
architecture that maintains the same functionality and output.
"""

import asyncio
import click
import sys
from typing import Optional
import logging
from pathlib import Path

from .commands import (
    GeneratePageCommand,
    TestConnectionCommand,
    FillQueueCommand,
    PopCommand,
    CreateListCommand,
    CreateScatterCommand,
)
from .services import ServiceContainer
from .services.neuron_discovery_service import InspectNeuronTypeCommand
from .models import NeuronTypeName
from .utils import get_git_version


# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_services(
    config_path: Optional[str] = None,
    verbose: bool = False,
    copy_mode: str = "check_exists",
) -> ServiceContainer:
    """Set up the service container with configuration."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Import config here to avoid circular imports
    from .config import Config

    # Load configuration
    config = Config.load(config_path or "config.yaml")

    return ServiceContainer(config, copy_mode)


@click.group(invoke_without_command=True)
@click.option("-c", "--config", help="Configuration file path")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option(
    "--version", is_flag=True, help="Show neuView version from git tags and exit"
)
@click.pass_context
def main(ctx, config: Optional[str], verbose: bool, version: bool):
    """neuView - Generate HTML pages for neuron types using modern DDD architecture."""
    if version:
        click.echo(get_git_version())
        ctx.exit()

    # If no subcommand is provided and no version flag, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()

    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose


@main.command("generate")
@click.option("--neuron-type", "-n", help="Neuron type to generate page for")
@click.option("--output-dir", help="Output directory")
@click.option(
    "--image-format",
    type=click.Choice(["svg", "png"], case_sensitive=False),
    default="svg",
    help="Format for hexagon grid images (default: svg)",
)
@click.option(
    "--embed/--no-embed",
    default=False,
    help="Embed images directly in HTML instead of saving to files",
)
@click.option(
    "--minify/--no-minify",
    default=True,
    help="Enable/disable HTML minification (default: enabled)",
)
@click.pass_context
def generate(
    ctx,
    neuron_type: Optional[str],
    output_dir: Optional[str],
    image_format: str,
    embed: bool,
    minify: bool,
):
    """Generate HTML pages for neuron types."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"], "force_all")

    async def run_generate():
        if neuron_type:
            # Generate for specific neuron type
            command = GeneratePageCommand(
                neuron_type=NeuronTypeName(neuron_type),
                output_directory=output_dir,
                image_format=image_format.lower(),
                embed_images=embed,
                minify=minify,
            )

            result = await services.page_service.generate_page(command)

            if result.is_ok():
                click.echo(f"✅ Generated page: {result.unwrap()}")
            else:
                click.echo(f"❌ Error: {result.unwrap_err()}", err=True)
                sys.exit(1)
        else:
            # Auto-discover and generate for multiple types
            try:
                # Use connector directly to discover neuron types
                discovered_types = services.neuprint_connector.discover_neuron_types(
                    services.config.discovery
                )
                type_names = list(discovered_types)[:20]  # Limit to 20 types

                if not type_names:
                    click.echo("No neuron types found.")
                    return
            except Exception as e:
                click.echo(f"❌ Error discovering types: {str(e)}", err=True)
                sys.exit(1)
            click.echo(f"Found {len(type_names)} neuron types. Generating pages...")

            # Generate pages with controlled concurrency
            max_concurrent = 3  # Default concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_single(type_name):
                async with semaphore:
                    command = GeneratePageCommand(
                        neuron_type=NeuronTypeName(type_name),
                        output_directory=output_dir,
                        image_format=image_format.lower(),
                        embed_images=embed,
                        minify=minify,
                    )

                    result = await services.page_service.generate_page(command)

                    if result.is_ok():
                        click.echo(f"✅ Generated: {type_name}")
                    else:
                        click.echo(f"❌ Failed {type_name}: {result.unwrap_err()}")

            tasks = [generate_single(type_name) for type_name in type_names]
            await asyncio.gather(*tasks, return_exceptions=True)

            click.echo(f"🎉 Completed bulk generation for {len(type_names)} types.")

    asyncio.run(run_generate())


@main.command("inspect")
@click.argument("neuron_type")
@click.pass_context
def inspect(ctx, neuron_type: str):
    """Inspect detailed information about a specific neuron type."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_inspect():
        command = InspectNeuronTypeCommand(
            neuron_type=NeuronTypeName(neuron_type),
        )

        result = await services.discovery_service.inspect_neuron_type(command)

        if result.is_err():
            click.echo(f"❌ Error: {result.unwrap_err()}", err=True)
            sys.exit(1)

        stats = result.unwrap()

        # Display detailed information
        click.echo(f"\n📊 {stats.type_name} Statistics")
        click.echo("=" * 50)

        click.echo("\n🧠 Neuron Counts:")
        click.echo(f"  Total:       {stats.total_count}")
        click.echo(f"  Left:        {stats.soma_side_counts.get('left', 0)}")
        click.echo(f"  Right:       {stats.soma_side_counts.get('right', 0)}")
        click.echo(f"  Middle:      {stats.soma_side_counts.get('middle', 0)}")

        if stats.total_count > 0:
            bilateral_ratio = stats.bilateral_ratio
            click.echo(f"  Bilateral ratio: {bilateral_ratio:.2f}")

        if stats.synapse_stats:
            click.echo("\n⚡ Synapse Statistics:")
            click.echo(f"  Avg Pre:     {stats.synapse_stats.get('avg_pre', 0):.1f}")
            click.echo(f"  Avg Post:    {stats.synapse_stats.get('avg_post', 0):.1f}")
            click.echo(f"  Avg Total:   {stats.synapse_stats.get('avg_total', 0):.1f}")
            click.echo(
                f"  Median:      {stats.synapse_stats.get('median_total', 0):.1f}"
            )
            click.echo(
                f"  Std Dev:     {stats.synapse_stats.get('std_dev_total', 0):.1f}"
            )

        click.echo(f"\n⏰ Computed: {stats.computed_at.strftime('%Y-%m-%d %H:%M:%S')}")

    asyncio.run(run_inspect())


@main.command("test-connection")
@click.option("--detailed", is_flag=True, help="Show detailed dataset information")
@click.option("--timeout", type=int, default=30, help="Connection timeout in seconds")
@click.pass_context
def test_connection(ctx, detailed: bool, timeout: int):
    """Test connection to the NeuPrint server."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_test():
        command = TestConnectionCommand(detailed=detailed, timeout=timeout)

        result = await services.connection_service.test_connection(command)

        if result.is_err():
            click.echo(f"❌ Connection failed: {result.unwrap_err()}", err=True)
            sys.exit(1)

        dataset_info = result.unwrap()

        click.echo("✅ Connection successful!")

        if detailed:
            click.echo("\n📡 Server Information:")
            click.echo(f"  Server:     {dataset_info.server_url}")
            click.echo(f"  Dataset:    {dataset_info.name}")
            click.echo(f"  Version:    {dataset_info.version}")
            click.echo(f"  Status:     {dataset_info.connection_status}")
        else:
            click.echo(f"Connected to {dataset_info.name} at {dataset_info.server_url}")

    asyncio.run(run_test())


@main.command("fill-queue")
@click.option("--neuron-type", "-n", help="Neuron type to generate queue entry for")
@click.option(
    "--all",
    "all_types",
    is_flag=True,
    help="Create queue files for all neuron types and update cache manifest",
)
@click.option("--output-dir", help="Output directory")
@click.option(
    "--image-format",
    type=click.Choice(["svg", "png"], case_sensitive=False),
    default="svg",
    help="Format for hexagon grid images (default: svg)",
)
@click.option(
    "--embed/--no-embed",
    default=False,
    help="Embed images directly in HTML instead of saving to files",
)
@click.pass_context
def fill_queue(
    ctx,
    neuron_type: Optional[str],
    all_types: bool,
    output_dir: Optional[str],
    image_format: str,
    embed: bool,
):
    """Create YAML queue files with generate command options and update JSON cache manifest."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_fill_queue():
        # Create the command with the appropriate parameters
        command = FillQueueCommand(
            neuron_type=NeuronTypeName(neuron_type) if neuron_type else None,
            output_directory=output_dir,
            image_format=image_format.lower(),
            embed_images=embed,
            all_types=all_types,
            max_types=10,  # Default limit when not using --all
            config_file=ctx.obj["config_path"],
        )

        result = await services.queue_service.fill_queue(command)

        if result.is_ok():
            if neuron_type:
                click.echo(
                    f"✅ Created queue file and updated JSON cache manifest: {result.unwrap()}"
                )
            else:
                click.echo(f"✅ {result.unwrap()}")
        else:
            click.echo(f"❌ Error: {result.unwrap_err()}", err=True)
            sys.exit(1)

    asyncio.run(run_fill_queue())


@main.command("pop")
@click.option("--output-dir", help="Output directory")
@click.option(
    "--minify/--no-minify",
    default=True,
    help="Enable/disable HTML minification (default: enabled)",
)
@click.pass_context
def pop(ctx, output_dir: Optional[str], minify: bool):
    """Pop and process a queue file."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_pop():
        command = PopCommand(output_directory=output_dir, minify=minify)

        result = await services.queue_service.pop_queue(command)

        if result.is_ok():
            click.echo(f"✅ {result.unwrap()}")
        else:
            click.echo(f"❌ Error: {result.unwrap_err()}", err=True)
            sys.exit(1)

    asyncio.run(run_pop())


@main.command("create-list")
@click.option("--output-dir", help="Output directory to scan for neuron pages")
@click.option(
    "--minify/--no-minify",
    default=True,
    help="Enable/disable HTML minification (default: enabled)",
)
@click.pass_context
def create_list(ctx, output_dir: Optional[str], minify: bool):
    """Generate an index page listing all available neuron types.

    Includes ROI analysis for comprehensive neuron information.
    """
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_create_list():
        command = CreateListCommand(
            output_directory=output_dir, include_roi_analysis=True, minify=minify
        )

        result = await services.index_service.create_index(command)

        if result.is_ok():
            generated_files = result.unwrap()
            if isinstance(generated_files, list):
                # Display main file first
                for file_path in generated_files:
                    click.echo(f"✅ Created: {file_path}")
            else:
                # Handle backward compatibility if single string returned
                click.echo(f"✅ Created index page: {generated_files}")
        else:
            click.echo(f"❌ Error: {result.unwrap_err()}", err=True)
            sys.exit(1)

    asyncio.run(run_create_list())


@main.command("create-scatter")
@click.pass_context
def create_scatter(ctx):
    """Generate three SVG scatterplots of spatial metrics for optic lobe types."""
    services = setup_services(ctx.obj["config_path"], ctx.obj["verbose"])

    async def run_create_scatter():

        await services.scatter_service.create_scatterplots()

        # Print the three scatterplot files that should have been created
        scfg = services.scatter_service.scatter_config
        scatter_dir = Path(scfg.scatter_dir)
        fname = scfg.scatter_fname

        for region in ("ME", "LO", "LOP"):
            file_path = scatter_dir / f"{region}_{fname}"
            if file_path.exists():
                click.echo(f"✅ Created: {file_path}")
            else:
                click.echo(f"⚠️ Expected but not found: {file_path}", err=True)

    asyncio.run(run_create_scatter())


if __name__ == "__main__":
    main()
