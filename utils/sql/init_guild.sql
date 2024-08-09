INSERT INTO guilds (
    id,
    prefix,
    bot_language,
    ratio_emoji,
    wordplay_enabled,
    sniper_enabled,
    sniper,
    antisniper_backup,
    command_settings,
    confess_cooldown,
    confess_channels,
    confess_banned,
    bot_logs_enabled
) VALUES (
    %s,    -- id
    %s,    -- prefix
    %s,    -- bot_language
    NULL,  -- ratio_emoji
    FALSE, -- wordplay_enabled
    TRUE,  -- sniper_enabled
    '[]',  -- sniper
    '{}',  -- antisniper_backup
    '{}',  -- command_settings
    3,     -- confess_cooldown
    '{}',  -- confess_channels
    '{}',  -- confess_banned
    FALSE  -- bot_logs_enabled
)