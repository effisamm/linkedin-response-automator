import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services import ai_service

class TestChromaDBPath(unittest.TestCase):

    @patch('chromadb.PersistentClient')
    def test_collection_path_matches_settings(self, mock_persistent_client):
        """
        Verify that the ChromaDB client is initialized with the path from settings.
        """
        # Mock the client and its methods to avoid actual file system interaction
        mock_client_instance = MagicMock()
        mock_persistent_client.return_value = mock_client_instance

        # Call the initialization function
        ai_service.initialize_resources()

        # Assert that PersistentClient was called with the correct path
        mock_persistent_client.assert_called_once_with(path=str(settings.CHROMADB_PATH))
        
        # Assert that the directory is created
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            ai_service.initialize_resources()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

if __name__ == '__main__':
    unittest.main()
