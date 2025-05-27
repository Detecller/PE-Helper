async def setup(bot):
    await bot.load_extension("cogs.members")
    await bot.load_extension("cogs.stats")
    await bot.load_extension("cogs.background_tasks")