import logging
import asyncio

class DiscordHandler(logging.Handler):
    def __init__(self, channel, level=logging.ERROR):
        super().__init__(level)
        self.channel = channel

    async def send_to_discord(self, message):
        try:
            await self.channel.send(f"⚠️ **Error Logged:** {message}")
        except Exception as e:
            print("Failed to send log to Discord:", e)

    def emit(self, record):
        try:
            message = self.format(record)
            asyncio.get_event_loop().create_task(self.send_to_discord(message))
        except Exception:
            self.handleError(record)