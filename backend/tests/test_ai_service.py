import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services import ai_service
from app.models.conversation import Conversation, Message, ConversationStage

class TestAIService(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize resources once for all tests in this class
        # Mock anthropic_client during initialization if it makes network calls
        with patch('anthropic.AsyncAnthropic') as MockAnthropic:
            MockAnthropic.return_value = MagicMock() # Ensure it returns a mock object
            ai_service.initialize_resources()

    @classmethod
    def tearDownClass(cls):
        # Close resources after all tests in this class
        ai_service.close_resources()

    @patch('app.services.ai_service.anthropic_client')
    async def test_detect_stage_scheduling(self, mock_anthropic_client):
        """
        Verify that detect_stage correctly identifies the SCHEDULING stage.
        """
        # Configure the mock Anthropic client to return a specific stage
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=ConversationStage.SCHEDULING.value)]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Create a conversation with a scheduling-related message
        messages = (
            Message(sender="User", text="Hi there!"),
            Message(sender="Other", text="Great to connect!"),
            Message(sender="User", text="Can we set up a call next week to discuss further?")
        )
        
        detected_stage = await ai_service.detect_stage(messages)
        
        self.assertEqual(detected_stage, ConversationStage.SCHEDULING)
        mock_anthropic_client.messages.create.assert_called_once()

    @patch('app.services.ai_service.anthropic_client')
    async def test_detect_stage_unknown_on_failure(self, mock_anthropic_client):
        """
        Verify that detect_stage returns UNKNOWN on API failure.
        """
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")

        messages = (
            Message(sender="User", text="Hello"),
        )
        
        detected_stage = await ai_service.detect_stage(messages)
        
        self.assertEqual(detected_stage, ConversationStage.UNKNOWN)
        mock_anthropic_client.messages.create.assert_called_once()

if __name__ == '__main__':
    unittest.main()
