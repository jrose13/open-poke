"""Message processor with Supabase database integration"""
import asyncio
from typing import Optional
import logging
from .agent import VoyagerAgent
from .models import Message
from .database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self, message_queue, notifier=None):
        self.agent = VoyagerAgent()
        self.message_queue = message_queue
        self.processing = False
        self.message_responses = {}  # Track responses by message_id
        self.notifier = notifier
    
    async def start_processing(self):
        """Start the message processing loop"""
        self.processing = True
        logger.info("Starting message processor...")
        
        while self.processing:
            try:
                # Get next message from queue
                try:
                    message = self.message_queue.pop()
                except IndexError:
                    message = None
                
                if message:
                    await self._process_message(message)
                else:
                    # No messages, wait
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in message processing loop: {type(e).__name__}")
                logger.debug(f"Full error details: {e}")
                await asyncio.sleep(5)
    
    async def stop_processing(self):
        """Stop the message processing loop"""
        self.processing = False
        logger.info("Stopping message processor...")
    
    async def _process_message(self, message: Message):
        """Process a single message and save to database"""
        try:
            logger.info(f"Processing message {message.message_id} from user {message.user_id}")

            # Get or create conversation for this user
            conversation = await db.get_or_create_active_conversation(message.user_id)
            
            # Save user message to database
            await db.create_message(
                conversation_id=conversation["id"],
                user_id=message.user_id,
                content=message.content,
                role="user"
            )

            # Process through agent
            response = await self.agent.process_message(message.user_id, message.content)

            # Store the response mapped to message_id (for polling)
            self.message_responses[message.message_id] = {
                "response": response,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "status": "completed"
            }

            # Save agent response to database
            await db.create_message(
                conversation_id=conversation["id"],
                user_id=message.user_id,
                content=response,
                role="assistant"
            )

            logger.info(f"Generated and saved response for message {message.message_id}")

            # Notify via WebSocket if connected
            if self.notifier:
                messages = await db.get_conversation_history_formatted(conversation["id"])
                await self.notifier.broadcast(
                    message.user_id,
                    {
                        "type": "conversation_update",
                        "conversations": messages,
                    },
                )

        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {type(e).__name__}")
            logger.debug(f"Full error details: {e}")
            
            # Store error response
            error_text = "Sorry, I encountered an error processing your message."
            self.message_responses[message.message_id] = {
                "response": error_text,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "status": "error"
            }
            
            # Try to save error to database
            try:
                conversation = await db.get_or_create_active_conversation(message.user_id)
                await db.create_message(
                    conversation_id=conversation["id"],
                    user_id=message.user_id,
                    content=error_text,
                    role="assistant"
                )
            except Exception as db_error:
                logger.error(f"Failed to save error to database: {db_error}")

    
    async def queue_user_message(self, user_id: str, content: str) -> str:
        """Queue a user message for processing and return message_id"""
        try:
            import uuid
            message_id = str(uuid.uuid4())
            
            message = Message(
                user_id=user_id,
                content=content,
                message_type="user",
                message_id=message_id
            )
            
            # Mark as processing
            self.message_responses[message_id] = {
                "response": None,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "status": "processing"
            }
            
            self.message_queue.appendleft(message)
            return message_id
            
        except Exception as e:
            logger.error(f"Error queuing message: {type(e).__name__}")
            logger.debug(f"Full error details: {e}")
            return ""
    
    def get_message_response(self, message_id: str) -> dict:
        """Get response for a specific message_id"""
        return self.message_responses.get(message_id, {"status": "not_found"})

