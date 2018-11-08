import asyncio
import async_timeout
import aiohttp


class DiscordAttachmentHandler:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    @staticmethod
    async def fetch_json(session, url):
        async with async_timeout.timeout(10):
            async with session.get(url) as response:
                return await response.json()

    async def get_content(self, url):
        async with aiohttp.ClientSession() as session:
            return await self.fetch_json(session, url)

    def get_ship_list(self, file_url, logger):
        try:
            return self.loop.run_until_complete(self.get_content(file_url))
        except asyncio.TimeoutError:
            logger.error("Could not download attachment. Asyncio timeout error.")
