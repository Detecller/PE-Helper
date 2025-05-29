from discord import app_commands
import logging


# Get logger
logger = logging.getLogger("pe_helper")


def has_allowed_role_and_channel(forbidden_roles: list[str] = None, forbidden_channels: list[str] = None):
    default_allowed_roles = {'Admin', 'Current EXCO', 'Member', 'Alumni'}
    default_allowed_channels = {'🛠┃admin-discussions', '🧠┃exco-discussions', '💬┃general', '🤖┃bot-dev'}

    forbidden_roles = forbidden_roles or []
    forbidden_channels = forbidden_channels or []

    async def predicate(interaction):
        allowed_roles = default_allowed_roles - set(forbidden_roles)
        allowed_channels = default_allowed_channels - set(forbidden_channels)

        user_roles = {r.name for r in interaction.user.roles}
        channel_name = interaction.channel.name if interaction.channel else None

        if not (user_roles & allowed_roles):
            logger.warning(f"User {interaction.user} ({interaction.user.id}) blocked by role check. Roles: {user_roles}, Allowed roles: {allowed_roles}")
            await interaction.response.send_message("❌ You don't have the permitted role.", ephemeral=True)
            return False

        if channel_name not in allowed_channels:
            logger.warning(f"User {interaction.user} ({interaction.user.id}) blocked by channel check. Channel: {channel_name}, Allowed channels: {allowed_channels}")
            await interaction.response.send_message("❌ This command can't be used in this channel.", ephemeral=True)
            return False

        return True

    return app_commands.check(predicate)