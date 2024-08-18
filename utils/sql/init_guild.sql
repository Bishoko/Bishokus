INSERT INTO guilds (
    id,
    is_oomf,
    prefix,
    bot_language,
    ratio_emoji_up,
    ratio_emoji_down,
    wordplay_enabled,
    sniper_enabled,
    sniper,
    antisniper_backup,
    command_settings,
    confess_cooldown,
    confess_channels,
    confess_banned,
    bot_logs_enabled,
    bot_banned,
    bot_banned_type,
    bot_banned_reason,
    bot_banned_history
) VALUES (
    %s,    -- id
    FALSE, -- is_oomf
    %s,    -- prefix
    %s,    -- bot_language
    NULL,  -- ratio_emoji_up
    NULL,  -- ratio_emoji_down
    FALSE, -- wordplay_enabled
    TRUE,  -- sniper_enabled
    '[]',  -- sniper
    '[]',  -- antisniper_backup
    '{}',  -- command_settings
    %s,     -- confess_cooldown
    '{}',  -- confess_channels
    '{}',  -- confess_banned
    FALSE, -- bot_logs_enabled
    FALSE, -- bot_banned
    NULL,  -- bot_banned_type
    NULL,  -- bot_banned_reason
    '[]'   -- bot_banned_history
)