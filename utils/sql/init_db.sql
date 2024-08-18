CREATE TABLE IF NOT EXISTS bot (
    vips JSON,
    donators JSON,
    donations JSON,
    support_tickets JSON,
    support_tickets_ban JSON,
    GIFs_enabled BOOL,
    GIFs_sus_enabled BOOL,
    GIFs_supernut_enabled BOOL
);

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_oomf BOOL,
    is_vip BOOL,
    vip_end DATE,
    bot_language TINYTEXT,
    bot_reply BOOL,
    first_dm_received BOOL,
    dms_accepted BOOL,
    dms_anon_accepted BOOL,
    dms_pub_accepted BOOL,
    wordplay_enabled BOOL,
    howgay_enabled BOOL,
    howgay_min INT,
    howgay_max INT,
    birthday DATE,
    bot_banned BOOL,
    bot_banned_type TINYTEXT,
    bot_banned_reason TINYTEXT,
    bot_banned_history JSON
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    is_oomf BOOL,
    prefix TINYTEXT,
    bot_language TINYTEXT,
    ratio_emoji_up BIGINT,
    ratio_emoji_down BIGINT,
    wordplay_enabled BOOL,
    sniper_enabled BOOL,
    sniper JSON,
    antisniper_backup JSON,
    command_settings JSON,
    confess_cooldown BIGINT,
    confess_channels JSON,
    confess_banned JSON,
    bot_logs_enabled BOOL,
    bot_banned BOOL,
    bot_banned_type TINYTEXT,
    bot_banned_reason TINYTEXT,
    bot_banned_history JSON
);

CREATE TABLE IF NOT EXISTS guild_count (
    `time` TIMESTAMP PRIMARY KEY,
    count INT
);

CREATE TABLE IF NOT EXISTS message_logs (
    `time` TIMESTAMP PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    guild_name TINYTEXT,
    user_name TINYTEXT,
    raw_message TEXT(10000)
);

CREATE TABLE IF NOT EXISTS confess (
    id INT PRIMARY KEY,
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT,
    guild_name TINYTEXT,
    channel_name TINYTEXT,
    user_name TINYTEXT,
    raw_message TEXT(10000),
    `time` TIMESTAMP
);
