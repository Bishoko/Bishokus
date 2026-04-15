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
    vip_end TINYTEXT,
    bot_language TINYTEXT,
    bot_reply BOOL,
    first_dm_received BOOL,
    dms_accepted BOOL,
    dms_anon_accepted BOOL,
    dms_pub_accepted BOOL,
    gif_ratios_enabled BOOL,
    wordplay_enabled BOOL,
    howgay_enabled BOOL,
    howgay_min INT,
    howgay_max INT,
    birthday DATE,
    bot_banned BOOL,
    bot_banned_type TINYTEXT,
    bot_banned_reason TEXT(10000),
    bot_banned_history JSON
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT PRIMARY KEY,
    is_oomf BOOL,
    prefix TINYTEXT,
    bot_language TINYTEXT,
    ratio_emoji_up TINYTEXT,
    ratio_emoji_down TINYTEXT,
    gif_ratios_enabled BOOL,
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
    bot_banned_reason TEXT(10000),
    bot_banned_history JSON
);

CREATE TABLE IF NOT EXISTS guild_count (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `time` TIMESTAMP,
    count INT
);

CREATE TABLE IF NOT EXISTS message_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `time` TIMESTAMP,
    guild_id BIGINT,
    user_id BIGINT,
    guild_name TINYTEXT,
    user_name TINYTEXT,
    raw_message TEXT(10000)
);

CREATE TABLE IF NOT EXISTS confess (
    id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT,
    guild_name TINYTEXT,
    channel_name TINYTEXT,
    user_name TINYTEXT,
    raw_message TEXT(10000),
    `time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_usage_counters (
    command_name VARCHAR(256) PRIMARY KEY,
    usage_count INT,
    usage_count_slash INT,
    usage_count_text INT,
    last_used TIMESTAMP
);

CREATE TABLE IF NOT EXISTS command_usage_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    command_name TINYTEXT,
    command_args JSON DEFAULT NULL,
    command_args_str TEXT(10000) DEFAULT NULL,
    user_id BIGINT,
    guild_id BIGINT,
    slash_command BOOL,
    text_command_alias TINYTEXT DEFAULT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
