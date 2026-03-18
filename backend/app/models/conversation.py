from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import uuid

class ConversationStage(str, Enum):
    INITIAL_REPLY = "initial_reply"
    QUESTION = "question"
    INTEREST = "interest"
    OBJECTION = "objection"
    SCHEDULING = "scheduling"
    UNKNOWN = "unknown"

class Message(BaseModel):
    sender: str
    text: str

class Conversation(BaseModel):
    messages: List[Message]
    stage: Optional[ConversationStage] = None
    client_id: Optional[str] = "default"

class FeedbackPayload(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_draft: str
    final_sent_message: str
    was_edited: bool
    conversation_context: Conversation
    client_id: Optional[str] = None
