import json
import secrets
import sqlite3
import string
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config import get_settings

DEFAULT_CATEGORIES = [
    {"slug": "rap-francais", "name": "Rap français", "description": "Rap / drill / cloud FR"},
    {"slug": "slow", "name": "Slow", "description": "Ballades & slows"},
    {"slug": "variete-francaise", "name": "Variété française", "description": "Chanson française"},
    {"slug": "international", "name": "International", "description": "Hits hors FR"},
    {"slug": "artistes-anglais", "name": "Artistes anglais", "description": "Artistes anglophones"},
    {"slug": "musique-chinoise", "name": "Musique chinoise", "description": "Catalogue CN / C-pop"},
    {
        "slug": "mbole",
        "name": "Mbole",
        "description": "Rythme urbain camerounais (mbole) — https://www.youtube.com/results?search_query=mbole",
    },
    {
        "slug": "personnage-public-influenceur",
        "name": "Personnage public / influenceur",
        "description": "Punchlines d’influenceurs & figures publiques (Cameroun et ailleurs)",
    },
]


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote TEXT NOT NULL,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                year TEXT,
                genre TEXT,
                album TEXT,
                initials TEXT,
                UNIQUE(quote, artist, title)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_categories (
                quote_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (quote_id, category_id),
                FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                category_id INTEGER NOT NULL,
                host_token TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'lobby',
                round_limit INTEGER NOT NULL DEFAULT 10,
                mode TEXT NOT NULL DEFAULT 'classic',
                created_at TEXT DEFAULT (datetime('now')),
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
            """
        )
        # Migrate older parties tables
        party_cols = {r[1] for r in conn.execute("PRAGMA table_info(parties)").fetchall()}
        if "mode" not in party_cols:
            conn.execute("ALTER TABLE parties ADD COLUMN mode TEXT NOT NULL DEFAULT 'classic'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS party_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                party_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                player_token TEXT NOT NULL UNIQUE,
                is_host INTEGER NOT NULL DEFAULT 0,
                score INTEGER NOT NULL DEFAULT 0,
                finished INTEGER NOT NULL DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE,
                UNIQUE(party_id, name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS party_quotes (
                party_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                quote_id INTEGER NOT NULL,
                PRIMARY KEY (party_id, position),
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE,
                FOREIGN KEY (quote_id) REFERENCES quotes(id)
            )
            """
        )
        # Live bowling-style progress (safe on existing DBs)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(party_players)").fetchall()}
        if "progress" not in cols:
            conn.execute("ALTER TABLE party_players ADD COLUMN progress INTEGER NOT NULL DEFAULT 0")
        _seed_categories(conn)


def _seed_categories(conn: sqlite3.Connection) -> None:
    count = int(conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0])
    if count > 0:
        return
    for cat in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT INTO categories (slug, name, description) VALUES (?, ?, ?)",
            (cat["slug"], cat["name"], cat["description"]),
        )
    # Auto-assign existing quotes by heuristic genre/artist
    quotes = conn.execute("SELECT id, artist, title, genre FROM quotes").fetchall()
    cats = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM categories").fetchall()}
    for q in quotes:
        for slug in _guess_category_slugs(q["genre"] or "", q["artist"] or "", q["title"] or ""):
            cid = cats.get(slug)
            if cid:
                conn.execute(
                    "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
                    (q["id"], cid),
                )


def _guess_category_slugs(genre: str, artist: str, title: str) -> list[str]:
    g = (genre or "").lower()
    a = (artist or "").lower()
    blob = f"{g} {a} {title}".lower()
    slugs: list[str] = []
    if any(k in blob for k in ("rap", "drill", "cloud", "hip-hop", "hip hop", "urban")):
        if any(k in blob for k in ("français", "francais", "french", "ninho", "pnl", "damso", "gazo", "orelsan", "lomepal", "stromae", "iam")):
            slugs.append("rap-francais")
        else:
            slugs.append("international")
    if any(k in blob for k in ("slow", "ballad", "amour", "romant")):
        slugs.append("slow")
    if any(k in blob for k in ("variété", "variete", "chanson", "joe dassin", "christophe", "florent pagny")):
        slugs.append("variete-francaise")
    if any(k in blob for k in ("english", "anglais", "queen", "rihanna", "michael jackson", "daft punk", "pop", "rock", "electro", "french touch")):
        slugs.append("artistes-anglais")
        if "daft punk" not in a:
            slugs.append("international")
    if any(k in blob for k in ("chinois", "chinese", "c-pop", "mandarin", "cantonese", "中国")):
        slugs.append("musique-chinoise")
    if not slugs:
        if any(k in g for k in ("français", "francais", "french")):
            slugs.append("variete-francaise")
        else:
            slugs.append("international")
    # unique preserve order
    seen = set()
    out = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def row_to_quote(row: sqlite3.Row, category_ids: list[int] | None = None) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "quote": row["quote"],
        "artist": row["artist"],
        "title": row["title"],
        "hints": {
            "year": row["year"] or "",
            "genre": row["genre"] or "",
            "album": row["album"] or "",
            "initials": row["initials"] or "",
        },
    }
    if category_ids is not None:
        data["category_ids"] = category_ids
    return data


def list_quotes(conn: sqlite3.Connection, category_id: int | None = None) -> list[dict[str, Any]]:
    if category_id is None:
        rows = conn.execute("SELECT * FROM quotes ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            """
            SELECT q.* FROM quotes q
            JOIN quote_categories qc ON qc.quote_id = q.id
            WHERE qc.category_id = ?
            ORDER BY q.id
            """,
            (category_id,),
        ).fetchall()
    result = []
    for r in rows:
        cats = [
            int(x[0])
            for x in conn.execute(
                "SELECT category_id FROM quote_categories WHERE quote_id = ?", (r["id"],)
            ).fetchall()
        ]
        result.append(row_to_quote(r, cats))
    return result


def get_quote(conn: sqlite3.Connection, quote_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    if not row:
        return None
    cats = [
        int(x[0])
        for x in conn.execute(
            "SELECT category_id FROM quote_categories WHERE quote_id = ?", (quote_id,)
        ).fetchall()
    ]
    return row_to_quote(row, cats)


def random_quote(conn: sqlite3.Connection, category_id: int | None = None) -> dict[str, Any] | None:
    if category_id is None:
        row = conn.execute("SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1").fetchone()
    else:
        row = conn.execute(
            """
            SELECT q.* FROM quotes q
            JOIN quote_categories qc ON qc.quote_id = q.id
            WHERE qc.category_id = ?
            ORDER BY RANDOM() LIMIT 1
            """,
            (category_id,),
        ).fetchone()
    if not row:
        return None
    return get_quote(conn, row["id"])


def insert_quote(
    conn: sqlite3.Connection,
    *,
    quote: str,
    artist: str,
    title: str,
    year: str = "",
    genre: str = "",
    album: str = "",
    initials: str = "",
    category_ids: list[int] | None = None,
) -> dict[str, Any]:
    conn.execute(
        """
        INSERT INTO quotes (quote, artist, title, year, genre, album, initials)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(quote, artist, title) DO UPDATE SET
            year=excluded.year,
            genre=excluded.genre,
            album=excluded.album,
            initials=excluded.initials
        """,
        (quote.strip(), artist.strip(), title.strip(), year, genre, album, initials),
    )
    row = conn.execute(
        "SELECT * FROM quotes WHERE quote = ? AND artist = ? AND title = ?",
        (quote.strip(), artist.strip(), title.strip()),
    ).fetchone()
    if category_ids:
        for cid in category_ids:
            conn.execute(
                "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
                (row["id"], cid),
            )
    return get_quote(conn, row["id"])  # type: ignore[arg-type]


def delete_quote(conn: sqlite3.Connection, quote_id: int) -> bool:
    cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    return cur.rowcount > 0


def count_quotes(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0])


def seed_from_json(seed_path: Path) -> int:
    if not seed_path.exists():
        return 0
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    inserted = 0
    with get_db() as conn:
        if count_quotes(conn) > 0:
            # Still ensure categories seeded / assignments for existing empty mappings
            _ensure_quote_category_backfill(conn)
            return 0
        for item in data:
            hints = item.get("hints") or {}
            q = insert_quote(
                conn,
                quote=item["quote"],
                artist=item["artist"],
                title=item["title"],
                year=hints.get("year", ""),
                genre=hints.get("genre", ""),
                album=hints.get("album", ""),
                initials=hints.get("initials", ""),
            )
            # heuristic categories
            for slug in _guess_category_slugs(hints.get("genre", ""), item["artist"], item["title"]):
                row = conn.execute("SELECT id FROM categories WHERE slug = ?", (slug,)).fetchone()
                if row:
                    conn.execute(
                        "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
                        (q["id"], row["id"]),
                    )
            inserted += 1
    return inserted


def _ensure_quote_category_backfill(conn: sqlite3.Connection) -> None:
    """Assign categories to quotes that have none (e.g. DB created before categories)."""
    orphans = conn.execute(
        """
        SELECT q.id, q.artist, q.title, q.genre FROM quotes q
        LEFT JOIN quote_categories qc ON qc.quote_id = q.id
        WHERE qc.quote_id IS NULL
        """
    ).fetchall()
    if not orphans:
        return
    cats = {r["slug"]: r["id"] for r in conn.execute("SELECT id, slug FROM categories").fetchall()}
    for q in orphans:
        for slug in _guess_category_slugs(q["genre"] or "", q["artist"] or "", q["title"] or ""):
            cid = cats.get(slug)
            if cid:
                conn.execute(
                    "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
                    (q["id"], cid),
                )


# --- Categories ---

def list_categories(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.*, COUNT(qc.quote_id) AS quote_count
        FROM categories c
        LEFT JOIN quote_categories qc ON qc.category_id = c.id
        GROUP BY c.id
        ORDER BY c.name
        """
    ).fetchall()
    return [
        {
            "id": r["id"],
            "slug": r["slug"],
            "name": r["name"],
            "description": r["description"] or "",
            "quote_count": int(r["quote_count"]),
        }
        for r in rows
    ]


def get_category(conn: sqlite3.Connection, category_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not row:
        return None
    count = conn.execute(
        "SELECT COUNT(*) FROM quote_categories WHERE category_id = ?", (category_id,)
    ).fetchone()[0]
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"] or "",
        "quote_count": int(count),
    }


def create_category(conn: sqlite3.Connection, *, name: str, slug: str, description: str = "") -> dict[str, Any]:
    conn.execute(
        "INSERT INTO categories (slug, name, description) VALUES (?, ?, ?)",
        (slug.strip().lower(), name.strip(), description.strip()),
    )
    row = conn.execute("SELECT id FROM categories WHERE slug = ?", (slug.strip().lower(),)).fetchone()
    return get_category(conn, row["id"])  # type: ignore[arg-type]


def delete_category(conn: sqlite3.Connection, category_id: int) -> bool:
    cur = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    return cur.rowcount > 0


def set_quote_categories(conn: sqlite3.Connection, quote_id: int, category_ids: list[int]) -> dict[str, Any] | None:
    if not get_quote(conn, quote_id):
        return None
    conn.execute("DELETE FROM quote_categories WHERE quote_id = ?", (quote_id,))
    for cid in category_ids:
        conn.execute(
            "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
            (quote_id, cid),
        )
    return get_quote(conn, quote_id)


def add_quotes_to_category(conn: sqlite3.Connection, category_id: int, quote_ids: list[int]) -> int:
    if not get_category(conn, category_id):
        return -1
    n = 0
    for qid in quote_ids:
        if get_quote(conn, qid):
            conn.execute(
                "INSERT OR IGNORE INTO quote_categories (quote_id, category_id) VALUES (?, ?)",
                (qid, category_id),
            )
            n += 1
    return n


def remove_quote_from_category(conn: sqlite3.Connection, category_id: int, quote_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM quote_categories WHERE category_id = ? AND quote_id = ?",
        (category_id, quote_id),
    )
    return cur.rowcount > 0


# --- Parties ---

def _gen_code(conn: sqlite3.Connection) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(40):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        exists = conn.execute("SELECT 1 FROM parties WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code
    raise RuntimeError("Unable to generate unique party code")


def create_party(
    conn: sqlite3.Connection,
    *,
    category_id: int,
    host_name: str,
    round_limit: int = 10,
    mode: str = "classic",
) -> dict[str, Any]:
    cat = get_category(conn, category_id)
    if not cat:
        raise ValueError("category_not_found")
    quotes = list_quotes(conn, category_id)
    if not quotes:
        raise ValueError("category_empty")
    code = _gen_code(conn)
    host_token = secrets.token_urlsafe(24)
    player_token = secrets.token_urlsafe(24)
    mode_norm = "easy" if mode == "easy" else "classic"
    conn.execute(
        """
        INSERT INTO parties (code, category_id, host_token, status, round_limit, mode)
        VALUES (?, ?, ?, 'lobby', ?, ?)
        """,
        (code, category_id, host_token, max(1, min(round_limit, len(quotes))), mode_norm),
    )
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code,)).fetchone()
    conn.execute(
        """
        INSERT INTO party_players (party_id, name, player_token, is_host, score, finished)
        VALUES (?, ?, ?, 1, 0, 0)
        """,
        (party["id"], host_name.strip()[:40], player_token),
    )
    return party_snapshot(conn, code, include_tokens_for=player_token)


def join_party(conn: sqlite3.Connection, *, code: str, player_name: str) -> dict[str, Any]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    if party["status"] != "lobby":
        raise ValueError("party_not_joinable")
    player_token = secrets.token_urlsafe(24)
    try:
        conn.execute(
            """
            INSERT INTO party_players (party_id, name, player_token, is_host, score, finished)
            VALUES (?, ?, ?, 0, 0, 0)
            """,
            (party["id"], player_name.strip()[:40], player_token),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("name_taken") from exc
    return party_snapshot(conn, party["code"], include_tokens_for=player_token)


def start_party(conn: sqlite3.Connection, *, code: str, host_token: str) -> dict[str, Any]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    if party["host_token"] != host_token:
        raise ValueError("forbidden")
    if party["status"] != "lobby":
        raise ValueError("already_started")
    quotes = list_quotes(conn, party["category_id"])
    if not quotes:
        raise ValueError("category_empty")
    # Shuffle and freeze order
    import random

    random.shuffle(quotes)
    limit = min(int(party["round_limit"]), len(quotes))
    selected = quotes[:limit]
    conn.execute("DELETE FROM party_quotes WHERE party_id = ?", (party["id"],))
    for i, q in enumerate(selected):
        conn.execute(
            "INSERT INTO party_quotes (party_id, position, quote_id) VALUES (?, ?, ?)",
            (party["id"], i, q["id"]),
        )
    conn.execute(
        "UPDATE parties SET status = 'playing', started_at = datetime('now') WHERE id = ?",
        (party["id"],),
    )
    return party_snapshot(conn, party["code"])


def party_quotes(conn: sqlite3.Connection, code: str) -> list[dict[str, Any]]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    if party["status"] == "lobby":
        raise ValueError("not_started")
    rows = conn.execute(
        """
        SELECT q.* FROM party_quotes pq
        JOIN quotes q ON q.id = pq.quote_id
        WHERE pq.party_id = ?
        ORDER BY pq.position
        """,
        (party["id"],),
    ).fetchall()
    return [row_to_quote(r) for r in rows]


def update_player_score(
    conn: sqlite3.Connection,
    *,
    code: str,
    player_token: str,
    score: int,
    finished: bool = False,
    progress: int | None = None,
) -> dict[str, Any]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    player = conn.execute(
        "SELECT * FROM party_players WHERE party_id = ? AND player_token = ?",
        (party["id"], player_token),
    ).fetchone()
    if not player:
        raise ValueError("player_not_found")
    prog = int(progress) if progress is not None else int(player["progress"] if "progress" in player.keys() else 0)
    if finished:
        # Snap to full round count when done
        round_limit = int(party["round_limit"] or 0)
        prog = max(prog, round_limit)
    conn.execute(
        "UPDATE party_players SET score = ?, finished = ?, progress = ? WHERE id = ?",
        (max(0, int(score)), 1 if finished else 0, max(0, prog), player["id"]),
    )
    # Auto-finish party when all players finished
    if finished:
        pending = conn.execute(
            "SELECT COUNT(*) FROM party_players WHERE party_id = ? AND finished = 0",
            (party["id"],),
        ).fetchone()[0]
        if pending == 0 and party["status"] == "playing":
            conn.execute(
                "UPDATE parties SET status = 'finished', finished_at = datetime('now') WHERE id = ?",
                (party["id"],),
            )
    return party_snapshot(conn, party["code"], include_tokens_for=player_token)


def party_snapshot(
    conn: sqlite3.Connection,
    code: str,
    include_tokens_for: str | None = None,
) -> dict[str, Any]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    cat = get_category(conn, party["category_id"])
    quote_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM party_quotes WHERE party_id = ?", (party["id"],)
        ).fetchone()[0]
    )
    total_rounds = quote_count or int(party["round_limit"] or 0)
    players_rows = conn.execute(
        """
        SELECT id, name, is_host, score, finished, progress, player_token
        FROM party_players WHERE party_id = ?
        ORDER BY score DESC, progress DESC, joined_at ASC
        """,
        (party["id"],),
    ).fetchall()
    me = None
    players = []
    for p in players_rows:
        prog = int(p["progress"] or 0)
        item = {
            "id": p["id"],
            "name": p["name"],
            "is_host": bool(p["is_host"]),
            "score": int(p["score"]),
            "finished": bool(p["finished"]),
            "progress": prog,
            "total": total_rounds,
        }
        players.append(item)
        if include_tokens_for and p["player_token"] == include_tokens_for:
            me = {
                **item,
                "player_token": p["player_token"],
                "host_token": party["host_token"] if p["is_host"] else None,
            }
    return {
        "id": party["id"],
        "code": party["code"],
        "status": party["status"],
        "round_limit": int(party["round_limit"]),
        "mode": party["mode"] if "mode" in party.keys() else "classic",
        "category": cat,
        "players": players,
        "me": me,
        "quote_count": quote_count,
    }
