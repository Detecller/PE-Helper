from discord import app_commands
import logging


# Get logger
logger = logging.getLogger("pe_helper")


def has_allowed_role_and_channel(allowed_roles: list[str] = None, allowed_channels: list[str] = None):

    # Set default allowed roles & channels
    default_roles = {'Admin', 'Current EXCO', 'Member', 'Alumni'}
    default_channels = {
        '💬┃general-commands',
        '📖┃music-sheets',
        '👑┃exco-exclusive',
        '⚙️┃admin-related',
        '🎶┃music-radio-tools',
        '🚧┃test-commands'
    }

    allowed_roles = set(allowed_roles) if allowed_roles is not None else default_roles
    allowed_channels = set(allowed_channels) if allowed_channels is not None else default_channels

    async def predicate(interaction):
        user_roles = {role.name for role in interaction.user.roles}
        channel_name = interaction.channel.name if interaction.channel else None

        # Role whitelist check
        if not (user_roles & allowed_roles):
            logger.warning(f"User {interaction.user} ({interaction.user.id}) blocked by role whitelist. Roles: {user_roles}, Allowed: {allowed_roles}")
            await interaction.response.send_message("❌ You don't have the required role to use this command.", ephemeral=True)
            return False

        # Channel whitelist check
        if channel_name not in allowed_channels:
            logger.warning(f"User {interaction.user} ({interaction.user.id}) blocked by channel whitelist. Channel: {channel_name}, Allowed: {allowed_channels}")
            await interaction.response.send_message("❌ This command is not allowed in this channel.", ephemeral=True)
            return False

        return True

    return app_commands.check(predicate)