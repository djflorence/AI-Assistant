from typing import List, Dict
import re
from datetime import datetime

class SummarizationService:
    def __init__(self):
        self.summary_cache = {}

    def _clean_message(self, message: str) -> str:
        # Remove code blocks and special characters
        message = re.sub(r'```[\s\S]*?```', '[code block]', message)
        message = re.sub(r'`.*?`', '[code]', message)
        return message.strip()

    def summarize_conversation(self, messages: List[Dict]) -> str:
        # Create a concise summary of the conversation
        if not messages:
            return "No conversation to summarize."

        summary = []
        current_topic = ""
        message_count = len(messages)

        for idx, msg in enumerate(messages):
            content = self._clean_message(msg['content'])
            role = msg['role']

            if idx == 0:
                summary.append(f"Conversation started with: {content[:100]}...")
            elif idx == message_count - 1:
                summary.append(f"Latest message ({role}): {content[:100]}...")

        # Add statistics
        summary.append(f"\nStatistics:")
        summary.append(f"- Total messages: {message_count}")
        summary.append(f"- User messages: {sum(1 for m in messages if m['role'] == 'user')}")
        summary.append(f"- Assistant messages: {sum(1 for m in messages if m['role'] == 'assistant')}")

        return "\n".join(summary)

    def get_key_points(self, messages: List[Dict]) -> List[str]:
        # Extract key points from the conversation
        key_points = []
        for msg in messages:
            content = self._clean_message(msg['content'])
            # Look for sentences that might be important
            if any(marker in content.lower() for marker in 
                  ['important', 'key', 'must', 'should', 'remember', 'note']):
                key_points.append(content)
        return key_points[:5]  # Return top 5 key points

    def create_topic_clusters(self, messages: List[Dict]) -> Dict[str, List[str]]:
        # Group messages by topic
        topics = {}
        current_topic = "General"
        
        for msg in messages:
            content = self._clean_message(msg['content'])
            # Try to identify topic changes
            if msg['role'] == 'user' and len(content.split()) <= 10:
                current_topic = content
            
            if current_topic not in topics:
                topics[current_topic] = []
            topics[current_topic].append(content)

        return topics
