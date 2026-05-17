"""
Connection Test Service for neuView.

This service handles testing NeuPrint connections and returning
dataset information.
"""

import logging
from ..result import Result, Ok, Err
from ..commands import TestConnectionCommand, DatasetInfo

logger = logging.getLogger(__name__)


class ConnectionTestService:
    """Service for testing NeuPrint connection."""

    def __init__(self, neuprint_connector):
        """Initialize connection test service.

        Args:
            neuprint_connector: NeuPrint connector instance
        """
        self.connector = neuprint_connector

    async def test_connection(
        self, command: TestConnectionCommand
    ) -> Result[DatasetInfo, str]:
        """Test connection to NeuPrint server."""
        try:
            info = self.connector.test_connection()

            dataset_info = DatasetInfo(
                name=info.get("dataset", "Unknown"),
                version=info.get("version", "Unknown"),
                server_url=info.get("server", "Unknown"),
                connection_status="Connected",
            )

            return Ok(dataset_info)

        except Exception as e:
            return Err(f"Connection test failed: {str(e)}")

