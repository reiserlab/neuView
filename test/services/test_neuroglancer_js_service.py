"""
Tests for NeuroglancerJSService

This module tests the NeuroglancerJSService class, particularly the integration
with the neuroglancer base URL configuration parameter.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from jinja2 import Environment, DictLoader

from neuview.services.neuroglancer_js_service import NeuroglancerJSService


class MockConfig:
    """Mock configuration object for testing."""

    def __init__(
        self,
        dataset="hemibrain:v1.2.1",
        neuroglancer_base_url="https://clio-ng.janelia.org/",
    ):
        self.neuprint = Mock()
        self.neuprint.dataset = dataset
        self.neuprint.server = "neuprint.janelia.org"

        self.neuroglancer = Mock()
        self.neuroglancer.base_url = neuroglancer_base_url


class TestNeuroglancerJSService:
    """Test cases for NeuroglancerJSService."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock neuroglancer templates
        self.neuroglancer_templates = {
            "neuroglancer.js.jinja": '{"title": "{{ website_title }}", "dataset": "standard"}',
            "neuroglancer-fafb.js.jinja": '{"title": "{{ website_title }}", "dataset": "fafb"}',
        }

        # Create mock JavaScript template that uses the neuroglancer_base_url parameter
        self.js_template = """
// Neuroglancer URL Generator JavaScript
const NEUROGLANCER_BASE_URL = "{{ neuroglancer_base_url }}";
const DATASET_NAME = "{{ dataset_name }}";

// Embedded neuroglancer template JSON
const NEUROGLANCER_TEMPLATE = {{ neuroglancer_json }};

function generateNeuroglancerUrl() {
    const encodedState = encodeURIComponent(JSON.stringify(NEUROGLANCER_TEMPLATE));
    return `${NEUROGLANCER_BASE_URL}/#!${encodedState}`;
}
"""

        # Combine all templates
        self.templates = {
            **self.neuroglancer_templates,
            "static/js/neuroglancer-url-generator.js.jinja": self.js_template,
        }

        # Create Jinja environment with mock templates
        self.jinja_env = Environment(loader=DictLoader(self.templates))

    def create_service(
        self,
        dataset="hemibrain:v1.2.1",
        neuroglancer_base_url="https://clio-ng.janelia.org/",
    ):
        """Create NeuroglancerJSService with specified configuration."""
        config = MockConfig(dataset, neuroglancer_base_url)
        return NeuroglancerJSService(config=config, jinja_env=self.jinja_env)

    def test_generates_js_with_correct_base_url(self):
        """Test that JavaScript is generated with the correct neuroglancer base URL."""
        base_url = "https://neuroglancer-demo.appspot.com/"
        service = self.create_service(neuroglancer_base_url=base_url)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            assert js_file.exists(), "JavaScript file should be created"

            content = js_file.read_text()

            # Verify the base URL is correctly embedded
            expected_line = f'const NEUROGLANCER_BASE_URL = "{base_url.rstrip("/")}";'
            assert expected_line in content, (
                f"Base URL should be embedded in JavaScript: {expected_line}"
            )

    def test_generates_js_with_default_base_url(self):
        """Test that JavaScript is generated with default base URL when not specified."""
        service = self.create_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify the default base URL is embedded
            expected_line = (
                'const NEUROGLANCER_BASE_URL = "https://clio-ng.janelia.org";'
            )
            assert expected_line in content, (
                "Default base URL should be embedded in JavaScript"
            )

    def test_generates_js_with_cns_base_url(self):
        """Test that JavaScript is generated with CNS-specific base URL."""
        cns_base_url = "https://neuroglancer-demo.appspot.com/"
        service = self.create_service(
            dataset="male-cns:v0.9", neuroglancer_base_url=cns_base_url
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify the CNS base URL is embedded
            expected_line = (
                f'const NEUROGLANCER_BASE_URL = "{cns_base_url.rstrip("/")}";'
            )
            assert expected_line in content, (
                f"CNS base URL should be embedded in JavaScript: {expected_line}"
            )

    def test_strips_trailing_slash_from_base_url(self):
        """Test that trailing slashes are properly stripped from base URL."""
        base_url_with_slash = "https://example.com/"
        service = self.create_service(neuroglancer_base_url=base_url_with_slash)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify trailing slash is stripped
            expected_line = 'const NEUROGLANCER_BASE_URL = "https://example.com";'
            assert expected_line in content, (
                "Trailing slash should be stripped from base URL"
            )

    def test_uses_standard_template_for_non_fafb_dataset(self):
        """Test that standard neuroglancer template is used for non-FAFB datasets."""
        service = self.create_service("hemibrain:v1.2.1")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify standard template was embedded
            assert '"dataset": "standard"' in content, (
                "Standard template should be used"
            )

    def test_uses_fafb_template_for_fafb_dataset(self):
        """Test that FAFB-specific template is used for FAFB datasets."""
        service = self.create_service("flywire-fafb:v783b")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify FAFB template was embedded
            assert '"dataset": "fafb"' in content, "FAFB template should be used"

    def test_dataset_name_is_embedded(self):
        """Test that dataset name is properly embedded in the JavaScript."""
        dataset_name = "test-dataset:v1.0"
        service = self.create_service(dataset_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Read the generated JavaScript file
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            content = js_file.read_text()

            # Verify dataset name is embedded
            expected_line = f'const DATASET_NAME = "{dataset_name}";'
            assert expected_line in content, (
                "Dataset name should be embedded in JavaScript"
            )

    def test_creates_output_directory_structure(self):
        """Test that the service creates the proper output directory structure."""
        service = self.create_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            assert success, "JavaScript generation should succeed"

            # Verify directory structure
            static_dir = output_dir / "static"
            js_dir = output_dir / "static" / "js"
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"

            assert static_dir.exists(), "Static directory should be created"
            assert js_dir.exists(), "JS directory should be created"
            assert js_file.exists(), "JavaScript file should be created"

    @patch("neuview.services.neuroglancer_js_service.logger")
    def test_logs_template_selection(self, mock_logger):
        """Test that template selection is logged."""
        service = self.create_service("flywire-fafb:v783b")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            service.generate_neuroglancer_js(output_dir)

            # Verify logging was called
            mock_logger.debug.assert_any_call(
                "Using Neuroglancer template: neuroglancer-fafb.js.jinja for dataset: flywire-fafb:v783b"
            )

    def test_get_neuroglancer_template_name(self):
        """Test the get_neuroglancer_template_name method."""
        # Test standard template selection
        service = self.create_service("hemibrain:v1.2.1")
        assert service.get_neuroglancer_template_name() == "neuroglancer.js.jinja"

        # Test FAFB template selection
        service_fafb = self.create_service("flywire-fafb:v783b")
        assert (
            service_fafb.get_neuroglancer_template_name()
            == "neuroglancer-fafb.js.jinja"
        )

    def test_validate_templates(self):
        """Test template validation functionality."""
        service = self.create_service()
        results = service.validate_templates()

        # Verify all expected templates are validated
        expected_templates = [
            "neuroglancer.js.jinja",
            "neuroglancer-fafb.js.jinja",
            "neuroglancer-url-generator.js.jinja",
        ]

        for template in expected_templates:
            assert template in results, f"Template {template} should be validated"
            assert results[template] is True, f"Template {template} should be available"

    def test_get_template_info(self):
        """Test the get_template_info method."""
        dataset = "test-dataset:v1.0"
        service = self.create_service(dataset)
        info = service.get_template_info()

        assert info["dataset"] == dataset, "Dataset should be included in template info"
        assert "selected_template" in info, "Selected template should be included"
        assert "template_validation" in info, "Template validation should be included"

    def test_atomic_write_leaves_no_temp_file(self):
        """After a successful write, only the final file should remain."""
        service = self.create_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)
            assert success

            js_dir = output_dir / "static" / "js"
            files = sorted(p.name for p in js_dir.iterdir())
            assert files == ["neuroglancer-url-generator.js"], (
                f"Expected only the final file, got: {files}"
            )

    def test_failed_rename_cleans_up_temp_file(self):
        """If os.replace raises, the temp file must not be left behind."""
        service = self.create_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            js_dir = output_dir / "static" / "js"

            with patch(
                "neuview.utils.atomic_write.os.replace",
                side_effect=OSError("simulated rename failure"),
            ):
                success = service.generate_neuroglancer_js(output_dir)

            assert success is False
            # js_dir is created before the failed write; nothing should remain.
            leftover = list(js_dir.iterdir()) if js_dir.exists() else []
            assert leftover == [], f"Temp file leaked after rename failure: {leftover}"

    def test_concurrent_writes_produce_complete_file(self):
        """Concurrent generate calls must never leave a half-written file.

        Reproduces the parallel-pop-all race that triggered the
        'missing required function' error: with non-atomic writes, a
        reader observing the file mid-write would see truncated content.
        """
        import threading

        service = self.create_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            js_file = output_dir / "static" / "js" / "neuroglancer-url-generator.js"
            barrier = threading.Barrier(8)
            errors = []

            def worker():
                try:
                    barrier.wait(timeout=5)
                    assert service.generate_neuroglancer_js(output_dir)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert not errors, f"Worker errors: {errors}"
            content = js_file.read_text()
            # Every render must contain the embedded base URL marker —
            # a partial write would have truncated before this line.
            assert "const NEUROGLANCER_BASE_URL =" in content
            assert "function generateNeuroglancerUrl" in content

    def test_handles_template_error_gracefully(self):
        """Test that the service handles template errors gracefully."""
        # Create service with broken templates
        broken_templates = {
            "neuroglancer.js.jinja": "{{ invalid_syntax",  # Invalid JSON/template
            "static/js/neuroglancer-url-generator.js.jinja": self.js_template,
        }

        broken_env = Environment(loader=DictLoader(broken_templates))
        config = MockConfig()
        service = NeuroglancerJSService(config=config, jinja_env=broken_env)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            success = service.generate_neuroglancer_js(output_dir)

            # Should fail gracefully
            assert success is False, (
                "Should return False when template processing fails"
            )
