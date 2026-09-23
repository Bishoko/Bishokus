import bisect
import hashlib
import json
import math
import random
import time
from datetime import datetime, timedelta, timezone

from unidecode import unidecode

from utils.sql import get_db_connection
from utils.logger import log
from utils import config

ROLLS_PER_RESET = 10
ROLL_RESET_COOLDOWN = timedelta(minutes=40)

MIN_KAKERA_VALUE = 5
MAX_KAKERA_VALUE = 500


def _parse_json_field(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _guild_allowed(privated_guilds, guild_id: int) -> bool:
    guilds = _parse_json_field(privated_guilds)
    if not guilds:
        return True
    return any(str(guild) == str(guild_id) for guild in guilds)


def build_image_url(path: str | None) -> str | None:
    if not path:
        return None
    base_url = config.get("media-base-url", "").rstrip("/")
    return f"{base_url}{path}"


def get_rollable_character(gender: int | None, guild_id: int, allow_nsfw: bool) -> dict | None:
    """Pick a random character eligible for a roll, respecting the gender filter,
    per-guild privacy on both the character and its series, and NSFW gating."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        query = (
            "SELECT c.uuid, c.name, c.images, c.privated_guilds, c.claim_count, "
            "c.`rank`, c.like_count, c.like_rank, c.kakera_value, s.name, s.privated_guilds "
            "FROM mudae_characters c "
            "LEFT JOIN mudae_series s ON s.uuid = c.base_serie "
            "WHERE c.is_approved = 1 AND c.is_enabled = 1"
        )
        params = []

        if gender is not None:
            query += " AND c.gender = %s"
            params.append(gender)

        if not allow_nsfw:
            query += " AND c.is_nsfw = 0"

        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    eligible = []
    for (uuid, name, images, char_privated_guilds, claim_count, rank, like_count,
         like_rank, kakera_value, series_name, series_privated_guilds) in rows:
        if not _guild_allowed(char_privated_guilds, guild_id):
            continue
        if not _guild_allowed(series_privated_guilds, guild_id):
            continue

        eligible.append({
            "uuid": uuid,
            "name": name,
            "images": _parse_json_field(images) or [],
            "claim_count": claim_count or 0,
            "rank": rank,
            "like_count": like_count or 0,
            "like_rank": like_rank,
            "kakera_value": kakera_value,
            "series_name": series_name,
        })

    if not eligible:
        return None

    character = random.choice(eligible)
    character["owner_id"] = get_character_owner(character["uuid"], guild_id)
    return character


def get_character_owner(character_uuid: str, guild_id: int) -> int | None:
    """Ownership is server-exclusive: a character claimed in one guild isn't
    considered claimed in another. The current owner in a guild is whoever
    holds the active claim/gift there (is_active = 1); divorcing deactivates
    it instead of deleting it, so the claim history stays intact."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT user_id FROM mudae_claims "
            "WHERE character_uuid = %s AND guild_id = %s AND is_active = 1 "
            "ORDER BY claim_time DESC, id DESC LIMIT 1",
            (character_uuid, guild_id)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        cursor.close()
        connection.close()


def compute_kakera_reaction_reward(kakera_value: int) -> int:
    """Reward for reacting to an already-owned roll instead of claiming it."""
    return max(MIN_KAKERA_VALUE, (kakera_value or 0) // 2)


def add_kakera_reward(user_id: int, guild_id: int, amount: int):
    """Adds kakera without logging a claim: used for the reaction reward on
    already-owned rolls, which isn't a claim and shouldn't affect claim_count."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        _ensure_mudae_user(cursor, user_id, guild_id)
        cursor.execute(
            "UPDATE mudae_users SET kakera = kakera + %s WHERE user_id = %s AND guild_id = %s",
            (amount, user_id, guild_id)
        )
        cursor.fetchall()
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def _ensure_mudae_user(cursor, user_id: int, guild_id: int):
    cursor.execute(
        "INSERT INTO mudae_users (user_id, guild_id, kakera, rolls_used, rolls_reset_at) "
        "VALUES (%s, %s, 0, 0, NULL) "
        "ON DUPLICATE KEY UPDATE user_id = user_id",
        (user_id, guild_id)
    )
    cursor.fetchall()


def consume_roll(user_id: int, guild_id: int) -> tuple[bool, timedelta]:
    """Checks and consumes one roll for the user in this guild against the
    10-per-40min cooldown (rolls, like everything mudae besides likes, are
    server-exclusive - your rolls on one server don't affect another).
    Returns (allowed, time_until_reset). When allowed is True, the roll is
    already counted."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        _ensure_mudae_user(cursor, user_id, guild_id)

        cursor.execute(
            "SELECT rolls_used, rolls_reset_at FROM mudae_users WHERE user_id = %s AND guild_id = %s",
            (user_id, guild_id)
        )
        rolls_used, rolls_reset_at = cursor.fetchone()

        now = datetime.now()
        if rolls_reset_at is None or now >= rolls_reset_at:
            rolls_used = 0
            rolls_reset_at = now + ROLL_RESET_COOLDOWN

        if rolls_used >= ROLLS_PER_RESET:
            cursor.execute(
                "UPDATE mudae_users SET rolls_reset_at = %s WHERE user_id = %s AND guild_id = %s",
                (rolls_reset_at, user_id, guild_id)
            )
            connection.commit()
            return False, rolls_reset_at - now

        rolls_used += 1
        cursor.execute(
            "UPDATE mudae_users SET rolls_used = %s, rolls_reset_at = %s WHERE user_id = %s AND guild_id = %s",
            (rolls_used, rolls_reset_at, user_id, guild_id)
        )
        connection.commit()
        return True, rolls_reset_at - now
    finally:
        cursor.close()
        connection.close()


CLAIM_CYCLE = timedelta(hours=3)
_CLAIM_CYCLE_EPOCH = datetime(1970, 1, 1)


def _utc_now() -> datetime:
    """Naive UTC datetime matching what MySQL's NOW() writes into claim_time/
    like_time/unlike_time on this server (system_time_zone=UTC, session
    time_zone=SYSTEM). datetime.now() is local server time; comparing it
    against those columns silently drifts by the server's UTC offset, which
    broke the claim-cycle gate (claims never looked like they were "in" the
    current cycle, so it never blocked a re-claim)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _current_claim_cycle_start(now: datetime) -> datetime:
    """Claims are on a shared cycle: everyone's claim resets at the same
    wall-clock boundaries (every 3 hours since the Unix epoch), rather than a
    per-user timer that starts counting from their last claim."""
    cycle_seconds = CLAIM_CYCLE.total_seconds()
    elapsed_seconds = (now - _CLAIM_CYCLE_EPOCH).total_seconds()
    cycle_index = elapsed_seconds // cycle_seconds
    return _CLAIM_CYCLE_EPOCH + timedelta(seconds=cycle_index * cycle_seconds)


def get_claim_status(user_id: int, guild_id: int) -> tuple[bool, timedelta]:
    """Returns (can_claim, time_until_next_reset) for the current claim cycle
    in this guild. Server-exclusive like the rest of mudae besides likes:
    using your claim on one server doesn't block claiming on another."""
    now = _utc_now()
    cycle_start = _current_claim_cycle_start(now)
    next_reset = cycle_start + CLAIM_CYCLE

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM mudae_claims WHERE user_id = %s AND guild_id = %s AND claim_time >= %s",
            (user_id, guild_id, cycle_start)
        )
        claimed_this_cycle = cursor.fetchone()[0] > 0
    finally:
        cursor.close()
        connection.close()

    return not claimed_this_cycle, next_reset - now


def get_user_collection(user_id: int, guild_id: int) -> list[dict]:
    """Returns the characters the user currently owns in this guild (i.e.
    they hold the active claim/gift for it here), ordered by name. Ownership
    is server-exclusive, so this never crosses guild boundaries."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT c.uuid, c.name, c.aliases, c.images, c.gender, c.kakera_value, "
            "c.`rank`, c.like_rank, s.name, s.type "
            "FROM mudae_characters c "
            "LEFT JOIN mudae_series s ON s.uuid = c.base_serie "
            "WHERE c.uuid IN ("
            "  SELECT character_uuid FROM mudae_claims "
            "  WHERE guild_id = %s AND user_id = %s AND is_active = 1"
            ") "
            "ORDER BY c.name ASC",
            (guild_id, user_id)
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    collection = []
    for uuid, name, aliases, images, gender, kakera_value, rank, like_rank, series_name, series_type in rows:
        collection.append({
            "uuid": uuid,
            "name": name,
            "aliases": _parse_json_field(aliases) or [],
            "images": _parse_json_field(images) or [],
            "gender": gender if gender is not None else 0,
            "kakera_value": kakera_value or 0,
            "rank": rank,
            "like_rank": like_rank,
            "series_name": series_name,
            "series_type": series_type,
        })
    return collection


def match_owned_character(collection: list[dict], query: str) -> dict | None:
    """Matches a query against an already-fetched owned-character collection
    (see get_user_collection) by uuid (exact, case-sensitive), or by name/alias
    ignoring case (an exact-accent match is preferred, but accents are ignored
    if nothing matches otherwise). Split out from find_owned_character so
    callers that need to try several candidate queries against the same
    collection (e.g. disambiguating "!give <user> <character>" text, where the
    user portion length is unknown) don't re-fetch it on every attempt."""
    query = query.strip()
    if not query:
        return None

    for character in collection:
        if character["uuid"] == query:
            return character

    normalized_query = normalize_search_text(query)
    accent_insensitive_match = None
    for character in collection:
        if _match_rank(character, query) == 0:
            return character
        if accent_insensitive_match is None and normalized_query in _terms(character["name"], character["aliases"]):
            accent_insensitive_match = character

    return accent_insensitive_match


def find_owned_character(user_id: int, guild_id: int, query: str) -> dict | None:
    """Finds a character the user currently owns in this guild by uuid (exact,
    case-sensitive), or by name/alias ignoring case (an exact-accent match is
    preferred, but accents are ignored if nothing matches otherwise)."""
    return match_owned_character(get_user_collection(user_id, guild_id), query)


SEARCH_CACHE_TTL = 30  # seconds a loaded search catalog is reused
_search_cache: dict[str, tuple[float, list[dict]]] = {}


def normalize_search_text(value: str | None) -> str:
    """Case-, accent- and spacing-insensitive form used for all name matching
    ("Élève" -> "eleve", "cœur" -> "coeur"). Done in Python rather than SQL on
    purpose: DB collations differ per column (aliases are utf8mb4_bin), and
    aliases are stored as \\uXXXX-escaped JSON text SQL can't match against."""
    value = (value or "").strip()
    normalized = " ".join(unidecode(value).casefold().split())
    # Text with no transliteration (e.g. only emoji) falls back to itself.
    return normalized or " ".join(value.casefold().split())


def _terms(entry_name: str | None, aliases: list) -> list[str]:
    return [normalize_search_text(name) for name in [entry_name or ""] + [a for a in aliases if isinstance(a, str)]]


def _invalidate_search_cache():
    _search_cache.clear()


def _get_catalog(kind: str) -> list[dict]:
    """All approved (and enabled) characters or series with pre-normalized
    search terms, cached briefly so autocomplete doesn't query on every
    keystroke. Visibility (guild privacy, NSFW) is applied per search."""
    cached = _search_cache.get(kind)
    if cached and time.monotonic() - cached[0] < SEARCH_CACHE_TTL:
        return cached[1]

    if kind == "character":
        sql = (
            "SELECT c.uuid, c.name, c.aliases, c.privated_guilds, c.like_count, c.is_nsfw, s.name, s.privated_guilds "
            "FROM mudae_characters c LEFT JOIN mudae_series s ON s.uuid = c.base_serie "
            "WHERE c.is_approved = 1 AND c.is_enabled = 1"
        )
    else:
        sql = (
            "SELECT uuid, name, aliases, privated_guilds, like_count, is_nsfw, type, NULL "
            "FROM mudae_series WHERE is_approved = 1"
        )

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    catalog = []
    for uuid, name, aliases, privated, like_count, is_nsfw, detail, detail_privated in rows:
        aliases = _parse_json_field(aliases) or []
        catalog.append({
            "uuid": uuid,
            "name": name,
            "aliases": aliases,
            "like_count": like_count or 0,
            "detail": detail,
            "is_nsfw": bool(is_nsfw),
            "privated": _parse_json_field(privated),
            # A character is also hidden wherever its series is; series have no parent.
            "detail_privated": _parse_json_field(detail_privated) if kind == "character" else None,
            "terms": _terms(name, aliases),
        })

    _search_cache[kind] = (time.monotonic(), catalog)
    return catalog


def _match_rank(result: dict, query: str) -> int:
    """0 = uuid or exact name/alias (accents included), 1 = exact once accents
    are ignored, 2 = starts with the query, 3 = contains it."""
    query = query.strip()
    if result["uuid"] == query:
        return 0

    raw_query = " ".join(query.casefold().split())
    names = [result["name"] or ""] + [a for a in result["aliases"] if isinstance(a, str)]
    if any(" ".join(name.casefold().split()) == raw_query for name in names):
        return 0

    normalized_query = normalize_search_text(query)
    terms = _terms(result["name"], result["aliases"])
    if normalized_query in terms:
        return 1
    if any(term.startswith(normalized_query) for term in terms):
        return 2
    return 3


def _sort_results(results: list[dict], query: str) -> list[dict]:
    return sorted(
        results, key=lambda r: (_match_rank(r, query) if query else 3, -r["like_count"], r["name"] or "")
    )


def _search(kind: str, query: str, guild_id: int, allow_nsfw: bool, limit: int) -> list[dict]:
    query = query.strip()
    normalized_query = normalize_search_text(query)

    results = []
    for entry in _get_catalog(kind):
        if entry["is_nsfw"] and not allow_nsfw:
            continue
        if not _guild_allowed(entry["privated"], guild_id) or not _guild_allowed(entry["detail_privated"], guild_id):
            continue
        if query and entry["uuid"] != query and not any(normalized_query in term for term in entry["terms"]):
            continue
        results.append(entry)

    return _sort_results(results, query)[:limit]


def search_characters(query: str, guild_id: int, allow_nsfw: bool, limit: int = 25) -> list[dict]:
    """Searches approved/enabled characters by uuid, or by name/alias substring
    ignoring case and accents, honouring guild privacy on the character and its
    series plus NSFW gating. An empty query returns the most-liked characters."""
    return _search("character", query, guild_id, allow_nsfw, limit)


def search_series(query: str, guild_id: int, allow_nsfw: bool, limit: int = 25) -> list[dict]:
    """Same as search_characters, for series."""
    return _search("series", query, guild_id, allow_nsfw, limit)


def _pick_match(results: list[dict], query: str) -> tuple[dict | None, list[dict]]:
    """Returns (match, ambiguous_candidates): an exact match (accents ignored
    if need be) or a lone partial match wins outright, otherwise the top few
    candidates are suggested."""
    query = query.strip()
    if not query or not results:
        return None, []

    # Results arrive sorted by match quality then popularity, so the first is the best.
    if _match_rank(results[0], query) <= 1:
        return results[0], []
    if len(results) == 1:
        return results[0], []
    return None, results[:5]


def find_character(query: str, guild_id: int, allow_nsfw: bool) -> tuple[dict | None, list[dict]]:
    return _pick_match(search_characters(query, guild_id, allow_nsfw), query)


def find_series(query: str, guild_id: int, allow_nsfw: bool) -> tuple[dict | None, list[dict]]:
    return _pick_match(search_series(query, guild_id, allow_nsfw), query)


def _add_like(likes_table: str, uuid_column: str, target_table: str, user_id: int, target_uuid: str) -> bool:
    """Records an active like and bumps the cached like_count. Returns False
    if the user already actively likes it. Table/column names are internal
    constants, never user input."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT 1 FROM {likes_table} WHERE {uuid_column} = %s AND user_id = %s AND is_active = 1 LIMIT 1",  # nosec B608
            (target_uuid, user_id)
        )
        if cursor.fetchone():
            return False

        cursor.execute(
            f"INSERT INTO {likes_table} ({uuid_column}, user_id, like_time, is_active) VALUES (%s, %s, NOW(), 1)",  # nosec B608
            (target_uuid, user_id)
        )
        cursor.fetchall()
        cursor.execute(
            f"UPDATE {target_table} SET like_count = like_count + 1 WHERE uuid = %s",  # nosec B608
            (target_uuid,)
        )
        cursor.fetchall()
        connection.commit()
        _invalidate_search_cache()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def like_character(user_id: int, character_uuid: str) -> bool:
    return _add_like("mudae_characters_likes", "character_uuid", "mudae_characters", user_id, character_uuid)


def like_series(user_id: int, series_uuid: str) -> bool:
    return _add_like("mudae_series_likes", "serie_uuid", "mudae_series", user_id, series_uuid)


def _remove_like(likes_table: str, uuid_column: str, target_table: str, user_id: int, target_uuid: str) -> bool:
    """Deactivates the user's active like(s) (kept as history, with unlike_time
    recorded so weekly like_evolution can go negative) and lowers the cached
    like_count to match. Returns False if the user didn't actively like it."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE {likes_table} SET is_active = 0, unlike_time = NOW() "  # nosec B608
            f"WHERE {uuid_column} = %s AND user_id = %s AND is_active = 1",
            (target_uuid, user_id)
        )
        cursor.fetchall()
        removed = cursor.rowcount
        if removed < 1:
            connection.rollback()
            return False

        cursor.execute(
            f"UPDATE {target_table} SET like_count = GREATEST(like_count - %s, 0) WHERE uuid = %s",  # nosec B608
            (removed, target_uuid)
        )
        cursor.fetchall()
        connection.commit()
        _invalidate_search_cache()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def unlike_character(user_id: int, character_uuid: str) -> bool:
    return _remove_like("mudae_characters_likes", "character_uuid", "mudae_characters", user_id, character_uuid)


def unlike_series(user_id: int, series_uuid: str) -> bool:
    return _remove_like("mudae_series_likes", "serie_uuid", "mudae_series", user_id, series_uuid)


def _search_liked(rows, query: str, limit: int) -> list[dict]:
    query = query.strip()
    normalized_query = normalize_search_text(query)
    results, seen = [], set()
    for result in rows:
        if result["uuid"] in seen:
            continue
        terms = _terms(result["name"], result["aliases"])
        if query and result["uuid"] != query and not any(normalized_query in term for term in terms):
            continue
        seen.add(result["uuid"])
        results.append(result)
    return _sort_results(results, query)[:limit]


def search_liked_characters(user_id: int, query: str, guild_id: int, allow_nsfw: bool, limit: int = 25) -> list[dict]:
    """Searches only the characters the user currently likes (by uuid, name or
    alias substring). Hidden-in-this-guild ones are skipped like everywhere
    else, but disabled/unapproved ones stay findable so stale likes can still
    be removed."""
    sql = (
        "SELECT c.uuid, c.name, c.aliases, c.privated_guilds, c.like_count, s.name, s.privated_guilds "
        "FROM mudae_characters_likes l "
        "JOIN mudae_characters c ON c.uuid = l.character_uuid "
        "LEFT JOIN mudae_series s ON s.uuid = c.base_serie "
        "WHERE l.user_id = %s AND l.is_active = 1"
    )
    if not allow_nsfw:
        sql += " AND c.is_nsfw = 0"

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    visible = [
        {
            "uuid": uuid,
            "name": name,
            "aliases": _parse_json_field(aliases) or [],
            "like_count": like_count or 0,
            "detail": series_name,
        }
        for uuid, name, aliases, char_privated, like_count, series_name, series_privated in rows
        if _guild_allowed(char_privated, guild_id) and _guild_allowed(series_privated, guild_id)
    ]
    return _search_liked(visible, query, limit)


def search_liked_series(user_id: int, query: str, guild_id: int, allow_nsfw: bool, limit: int = 25) -> list[dict]:
    """Same as search_liked_characters, for series."""
    sql = (
        "SELECT s.uuid, s.name, s.aliases, s.privated_guilds, s.like_count, s.type "
        "FROM mudae_series_likes l "
        "JOIN mudae_series s ON s.uuid = l.serie_uuid "
        "WHERE l.user_id = %s AND l.is_active = 1"
    )
    if not allow_nsfw:
        sql += " AND s.is_nsfw = 0"

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    visible = [
        {
            "uuid": uuid,
            "name": name,
            "aliases": _parse_json_field(aliases) or [],
            "like_count": like_count or 0,
            "detail": series_type,
        }
        for uuid, name, aliases, privated_guilds, like_count, series_type in rows
        if _guild_allowed(privated_guilds, guild_id)
    ]
    return _search_liked(visible, query, limit)


def find_liked_character(user_id: int, query: str, guild_id: int, allow_nsfw: bool) -> tuple[dict | None, list[dict]]:
    return _pick_match(search_liked_characters(user_id, query, guild_id, allow_nsfw), query)


def find_liked_series(user_id: int, query: str, guild_id: int, allow_nsfw: bool) -> tuple[dict | None, list[dict]]:
    return _pick_match(search_liked_series(user_id, query, guild_id, allow_nsfw), query)


def get_user_likes(user_id: int, guild_id: int, allow_nsfw: bool) -> dict:
    """Returns the characters and series the user actively likes, hiding
    anything that isn't visible in this guild (privacy/NSFW) the same way
    rolls and searches do."""
    character_sql = (
        "SELECT c.uuid, c.name, c.privated_guilds, s.name, s.privated_guilds "
        "FROM mudae_characters_likes l "
        "JOIN mudae_characters c ON c.uuid = l.character_uuid "
        "LEFT JOIN mudae_series s ON s.uuid = c.base_serie "
        "WHERE l.user_id = %s AND l.is_active = 1 AND c.is_approved = 1 AND c.is_enabled = 1"
    )
    series_sql = (
        "SELECT s.uuid, s.name, s.privated_guilds "
        "FROM mudae_series_likes l "
        "JOIN mudae_series s ON s.uuid = l.serie_uuid "
        "WHERE l.user_id = %s AND l.is_active = 1 AND s.is_approved = 1"
    )
    if not allow_nsfw:
        character_sql += " AND c.is_nsfw = 0"
        series_sql += " AND s.is_nsfw = 0"
    character_sql += " ORDER BY c.name ASC"
    series_sql += " ORDER BY s.name ASC"

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(character_sql, (user_id,))
        character_rows = cursor.fetchall()
        cursor.execute(series_sql, (user_id,))
        series_rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    characters, seen = [], set()
    for uuid, name, char_privated, series_name, series_privated in character_rows:
        if uuid in seen:
            continue
        if not _guild_allowed(char_privated, guild_id) or not _guild_allowed(series_privated, guild_id):
            continue
        seen.add(uuid)
        characters.append({"uuid": uuid, "name": name, "series_name": series_name})

    series, seen = [], set()
    for uuid, name, privated_guilds in series_rows:
        if uuid in seen or not _guild_allowed(privated_guilds, guild_id):
            continue
        seen.add(uuid)
        series.append({"uuid": uuid, "name": name})

    return {"characters": characters, "series": series}


def transfer_character(character_uuid: str, to_user_id: int, guild_id: int):
    """Logs a gift: the receiver becomes the new current owner in this guild.
    Unlike a roll-claim, this doesn't award kakera or affect claim_count -
    it's a free transfer, not a fresh claim."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            "UPDATE mudae_claims SET is_active = 0 "
            "WHERE character_uuid = %s AND guild_id = %s AND is_active = 1",
            (character_uuid, guild_id)
        )
        cursor.fetchall()
        cursor.execute(
            "INSERT INTO mudae_claims (character_uuid, user_id, guild_id, kakera_value, claim_time, is_active) "
            "VALUES (%s, %s, %s, 0, NOW(), 1)",
            (character_uuid, to_user_id, guild_id)
        )
        cursor.fetchall()
        _ensure_mudae_user(cursor, to_user_id, guild_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def divorce_character(character_uuid: str, user_id: int, guild_id: int, kakera_value: int) -> int:
    """Releases a character the user owns in this guild, refunding a portion
    of its current kakera value. Deactivates the active claim rather than
    deleting it, so claim history stays intact. Doesn't touch claim_count -
    that's a lifetime popularity counter, and divorcing doesn't erase the
    fact it was claimed at some point."""
    refund = compute_kakera_reaction_reward(kakera_value)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            "UPDATE mudae_claims SET is_active = 0 "
            "WHERE character_uuid = %s AND guild_id = %s AND user_id = %s AND is_active = 1",
            (character_uuid, guild_id, user_id)
        )
        cursor.fetchall()

        _ensure_mudae_user(cursor, user_id, guild_id)
        cursor.execute(
            "UPDATE mudae_users SET kakera = kakera + %s WHERE user_id = %s AND guild_id = %s",
            (refund, user_id, guild_id)
        )
        cursor.fetchall()

        connection.commit()
        return refund
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_user_profile(user_id: int, guild_id: int) -> dict:
    """Returns the user's stats for this guild: collection size, a gender
    breakdown, their kakera balance here, and their highest-value claim (by
    current kakera_value, i.e. their most valuable asset right now). Server-
    exclusive like the rest of mudae besides likes."""
    collection = get_user_collection(user_id, guild_id)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT kakera FROM mudae_users WHERE user_id = %s AND guild_id = %s",
            (user_id, guild_id)
        )
        kakera_row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    gender_counts: dict[int, int] = {}
    most_valuable = None
    for character in collection:
        gender_counts[character["gender"]] = gender_counts.get(character["gender"], 0) + 1
        if most_valuable is None or character["kakera_value"] > most_valuable["kakera_value"]:
            most_valuable = character

    return {
        "collection_size": len(collection),
        "gender_counts": gender_counts,
        "kakera": (kakera_row[0] if kakera_row else 0) or 0,
        "most_valuable": most_valuable,
    }


def claim_character(character_uuid: str, user_id: int, guild_id: int, kakera_value: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        # Defensive: the roll flow only offers Claim when nobody currently
        # owns the character, so there shouldn't be an active row here -
        # but deactivate any stale one anyway rather than assume.
        cursor.execute(
            "UPDATE mudae_claims SET is_active = 0 "
            "WHERE character_uuid = %s AND guild_id = %s AND is_active = 1",
            (character_uuid, guild_id)
        )
        cursor.fetchall()

        cursor.execute(
            "INSERT INTO mudae_claims (character_uuid, user_id, guild_id, kakera_value, claim_time, is_active) "
            "VALUES (%s, %s, %s, %s, NOW(), 1)",
            (character_uuid, user_id, guild_id, kakera_value)
        )
        cursor.fetchall()

        cursor.execute(
            "UPDATE mudae_characters SET claim_count = claim_count + 1 WHERE uuid = %s",
            (character_uuid,)
        )
        cursor.fetchall()

        _ensure_mudae_user(cursor, user_id, guild_id)
        cursor.execute(
            "UPDATE mudae_users SET kakera = kakera + %s WHERE user_id = %s AND guild_id = %s",
            (kakera_value, user_id, guild_id)
        )
        cursor.fetchall()

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


EVOLUTION_WINDOW = timedelta(days=7)


def _rank_by(characters: list[dict], key: str) -> dict[str, int]:
    """Rank characters by a numeric key, descending (rank 1 = highest), with a
    stable tie-break on uuid so ties don't shuffle between runs."""
    ordered = sorted(characters, key=lambda c: (-c[key], c["uuid"]))
    return {c["uuid"]: index + 1 for index, c in enumerate(ordered)}


# What a character nobody has claimed or liked is worth: spread between these
# by a stable per-character seed, skewed low so the median stays near 20.
BASE_KAKERA_MIN = 10
BASE_KAKERA_MAX = 50
BASE_SKEW = 2
JITTER = 0.15  # +/- final variation per character, so equal-demand characters differ
DEMAND_SATURATION = 30  # claims + likes at which the absolute demand curve tops out
HOT_SATURATION = 10  # net claims + likes this week at which the hot bonus tops out
HOT_WEIGHT = 0.15
RATE_WEIGHT = 0.2


def _seed(uuid: str, salt: str) -> float:
    """Stable pseudo-random number in [0, 1) for a character. Derived from the
    uuid (not random(), and not hash(), which is salted per process) so a
    character keeps the same value across hourly recomputes and restarts
    instead of flickering."""
    digest = hashlib.sha256(f"{salt}:{uuid}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _curve(count: float, saturation: float) -> float:
    """Diminishing-returns 0..1 curve: the first few interactions matter most,
    and it tops out at `saturation`."""
    if count <= 0:
        return 0.0
    return min(math.log1p(count) / math.log1p(saturation), 1.0)


def _compute_kakera_value(
    character: dict, total: int, sorted_demands: list[int], rate_min: int | None, rate_max: int | None
) -> int:
    """Value follows demand: the more a character is claimed and liked, the
    more it's worth. A tunable starting point, not a fixed rule:

    - Absolute demand (claim_count + like_count, equal weight) on a log curve
      is the main driver, so one claim is worth little and value climbs as
      real engagement builds up.
    - Relative standing (share of characters with strictly less demand)
      scales that between 50% and 100%, so the most-wanted characters stand
      out from the pack. It's 0 for untouched characters, so ties at zero
      don't get spread out arbitrarily.
    - A hot bonus for net claims + likes over the trailing 7 days
      (claim_evolution + like_evolution) lifts trending characters.
    - `rate` (curated) nudges the value up or down when set; no effect at NULL.
    - Characters with no demand start from a per-character baseline
      (BASE_KAKERA_MIN..MAX) picked by a stable uuid-derived seed, and every
      value gets a small +/- JITTER from a second seed. This is fixed per
      character rather than re-rolled, so values don't change between runs.
    """
    demand = character["claim_count"] + character["like_count"]
    absolute = _curve(demand, DEMAND_SATURATION)
    relative = bisect.bisect_left(sorted_demands, demand) / max(total - 1, 1)
    popularity = absolute * (0.5 + 0.5 * relative)

    recent = max(character["claim_evolution"] + character["like_evolution"], 0)
    hot = _curve(recent, HOT_SATURATION)

    rate = character["rate"]
    if rate is None or rate_min is None or rate_max is None or rate_min == rate_max:
        rate_bonus = 0.0
    else:
        rate_bonus = RATE_WEIGHT * ((rate - rate_min) / (rate_max - rate_min) - 0.5)

    score = max(0.0, min(1.0, popularity + HOT_WEIGHT * hot + rate_bonus))

    baseline = BASE_KAKERA_MIN + (BASE_KAKERA_MAX - BASE_KAKERA_MIN) * _seed(character["uuid"], "base") ** BASE_SKEW
    value = baseline + (MAX_KAKERA_VALUE - baseline) * score
    value *= 1 - JITTER + 2 * JITTER * _seed(character["uuid"], "jitter")
    return max(MIN_KAKERA_VALUE, min(MAX_KAKERA_VALUE, round(value)))


def _read_stats_inputs():
    """Returns (character rows, claims/likes/unlikes over the trailing 7 days)
    or None when there are no approved characters."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id, uuid, claim_count, like_count, rate "
            "FROM mudae_characters WHERE is_approved = 1"
        )
        rows = cursor.fetchall()

        if not rows:
            return None

        since = _utc_now() - EVOLUTION_WINDOW
        cursor.execute(
            "SELECT character_uuid, COUNT(*) FROM mudae_claims "
            "WHERE claim_time >= %s GROUP BY character_uuid",
            (since,)
        )
        claims_last_week = dict(cursor.fetchall())

        cursor.execute(
            "SELECT character_uuid, COUNT(*) FROM mudae_characters_likes "
            "WHERE like_time >= %s GROUP BY character_uuid",
            (since,)
        )
        likes_last_week = dict(cursor.fetchall())

        cursor.execute(
            "SELECT character_uuid, COUNT(*) FROM mudae_characters_likes "
            "WHERE unlike_time >= %s GROUP BY character_uuid",
            (since,)
        )
        unlikes_last_week = dict(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()

    return rows, claims_last_week, likes_last_week, unlikes_last_week


def _build_character_stats(rows, claims_last_week, likes_last_week, unlikes_last_week) -> list[dict]:
    characters = []
    for char_id, uuid, claim_count, like_count, rate in rows:
        claim_count = claim_count or 0
        like_count = like_count or 0
        claim_evolution = claims_last_week.get(uuid, 0)
        # Net likes over the window: can be negative when likes are removed.
        like_evolution = likes_last_week.get(uuid, 0) - unlikes_last_week.get(uuid, 0)

        characters.append({
            "id": char_id,
            "uuid": uuid,
            "claim_count": claim_count,
            "like_count": like_count,
            "rate": rate,
            "claim_evolution": claim_evolution,
            "like_evolution": like_evolution,
            "claim_count_week_ago": max(claim_count - claim_evolution, 0),
            "like_count_week_ago": max(like_count - like_evolution, 0),
        })

    total = len(characters)
    rank_now = _rank_by(characters, "claim_count")
    rank_week_ago = _rank_by(characters, "claim_count_week_ago")
    like_rank_now = _rank_by(characters, "like_count")
    like_rank_week_ago = _rank_by(characters, "like_count_week_ago")

    rates = [c["rate"] for c in characters if c["rate"] is not None]
    rate_min, rate_max = (min(rates), max(rates)) if rates else (None, None)
    sorted_demands = sorted(c["claim_count"] + c["like_count"] for c in characters)

    for character in characters:
        uuid = character["uuid"]
        character["rank"] = rank_now[uuid]
        character["like_rank"] = like_rank_now[uuid]
        character["rank_evolution"] = rank_week_ago[uuid] - rank_now[uuid]
        character["like_rank_evolution"] = like_rank_week_ago[uuid] - like_rank_now[uuid]
        character["kakera_value"] = _compute_kakera_value(character, total, sorted_demands, rate_min, rate_max)

    return characters


def recompute_character_stats():
    """Re-rank all approved characters by claim_count and like_count, track
    claim/like movement over the trailing 7 days, and refresh kakera_value.
    These are cached columns, not computed live, so this needs to run
    periodically."""
    inputs = _read_stats_inputs()
    if inputs is None:
        return

    characters = _build_character_stats(*inputs)

    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        for character in characters:
            cursor.execute(
                "UPDATE mudae_characters SET `rank` = %s, rank_evolution = %s, "
                "like_rank = %s, like_rank_evolution = %s, claim_evolution = %s, "
                "like_evolution = %s, kakera_value = %s WHERE id = %s",
                (
                    character["rank"], character["rank_evolution"],
                    character["like_rank"], character["like_rank_evolution"],
                    character["claim_evolution"], character["like_evolution"],
                    character["kakera_value"], character["id"],
                )
            )
            cursor.fetchall()

        connection.commit()
        log.info(f"Recomputed mudae character stats for {len(characters)} characters.")
    except Exception as e:
        connection.rollback()
        log.exception(e, "Error recomputing mudae character stats")
    finally:
        cursor.close()
        connection.close()
