from typing import Any

from pydantic import BaseModel, Field


class Hints(BaseModel):
    year: str = ""
    genre: str = ""
    album: str = ""
    initials: str = ""


class QuoteOut(BaseModel):
    id: int
    quote: str
    artist: str
    title: str
    hints: Hints
    listen_url: str = ""
    rarity: str = "commune"
    contributor_pseudo: str = ""
    category_ids: list[int] = Field(default_factory=list)


class QuoteCreate(BaseModel):
    quote: str = Field(min_length=3)
    artist: str = Field(min_length=1)
    title: str = Field(min_length=1)
    hints: Hints | None = None
    listen_url: str = ""
    rarity: str = Field(default="commune", pattern="^(commune|rare|legendaire)$")
    category_ids: list[int] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    quote: str | None = Field(default=None, min_length=3)
    artist: str | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, min_length=1)
    listen_url: str | None = None
    rarity: str | None = Field(default=None, pattern="^(commune|rare|legendaire)$")


class QuotesBulkCreate(BaseModel):
    quotes: list[QuoteCreate] = Field(min_length=1)


class ImportRequest(BaseModel):
    artist: str = Field(min_length=1)
    title: str = Field(min_length=1)


class LyricsLine(BaseModel):
    index: int
    text: str
    candidate: bool = True


class ImportResponse(BaseModel):
    track: dict
    lyrics_lines: list[LyricsLine]
    hints: Hints


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str = ""
    quote_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str | None = None
    description: str = ""


class CategoryAssign(BaseModel):
    quote_ids: list[int] = Field(min_length=1)


class QuoteCategoriesSet(BaseModel):
    category_ids: list[int] = Field(default_factory=list)


class PartyCreate(BaseModel):
    category_id: int
    host_name: str = Field(min_length=1, max_length=40)
    round_limit: int = Field(default=10, ge=1, le=50)
    mode: str = Field(default="classic", pattern="^(classic|easy)$")


class PartyJoin(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    player_name: str = Field(min_length=1, max_length=40)


class PartyStart(BaseModel):
    host_token: str


class PartyScoreUpdate(BaseModel):
    """Progression / fin de partie. Le champ `score` est IGNORÉ (SEC-03) : le score est
    calculé côté serveur via POST /parties/{code}/answer ; il reste accepté pour
    compatibilité des anciens clients."""

    player_token: str
    score: int | None = Field(default=None, ge=0, description="Ignoré (SEC-03)")
    finished: bool = False
    progress: int | None = Field(default=None, ge=0, description="Index 1-based de la punchline en cours")


# --- MR-19 : événements analytics ---


class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    props: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    player_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    tz: str = Field(default="UTC", max_length=64)
    events: list[EventIn] = Field(min_length=1, max_length=50)


class EventBatchOut(BaseModel):
    accepted: int
    rejected: int
    day: str


# --- Refs du jour (lot A : règles serveur) ---


class DailyAnswerIn(BaseModel):
    quote_id: int
    artist: str = Field(default="", max_length=200)
    title: str = Field(default="", max_length=200)
    date: str | None = None
    category_key: str = "all"
    # Suivi serveur des réponses (MR-13 anti-triche) : optionnel pour rester
    # compatible, mais requis pour que POST /daily/result accepte le score.
    player_id: str | None = Field(default=None, min_length=8, max_length=64)
    hints_used: int = Field(default=0, ge=0, le=3, description="Indices consommés sur cette citation")
    skip: bool = Field(default=False, description="Citation passée sans réponse")


class DailyResultIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64)
    pseudo: str = Field(default="", max_length=200)
    score: int = Field(ge=0, le=5000)
    correct: int = Field(ge=0, le=5)
    hints: int = Field(ge=0, le=50)
    time_ms: int = Field(ge=0, le=86_400_000)
    grid: str = Field(default="", max_length=32)
    date: str | None = None
    category_id: int | None = None
    category_key: str | None = None
    # MR-14 : code du défi joué (si le joueur est arrivé par /d/<code>) → notification au créateur
    challenge_code: str | None = Field(default=None, max_length=16, pattern=r"^[A-Za-z0-9]+$")


class DailyChallengeCreateIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64)
    pseudo: str = Field(default="", max_length=200)
    score: int = Field(ge=0, le=5000)
    correct: int = Field(ge=0, le=5)
    grid: str = Field(default="", max_length=32)
    date: str | None = None
    category_id: int | None = None
    category_key: str | None = None


# --- Security by design (SEC-01 → SEC-03) ---------------------------------


class QuotePublicOut(BaseModel):
    """Vue « jeu » d'une punchline : jamais d'artiste, de titre ni de lien d'écoute."""

    id: int
    quote: str
    hints: Hints
    rarity: str = "commune"
    category_ids: list[int] = Field(default_factory=list)


class QuoteOptionsOut(BaseModel):
    artists: list[str]
    titles: list[str]


class QuoteAnswerIn(BaseModel):
    artist: str = Field(default="", max_length=120)
    title: str = Field(default="", max_length=120)
    hints_used: int = Field(default=0, ge=0, le=10)
    mode: str = Field(default="classic", pattern="^(classic|easy)$")


class QuoteReveal(BaseModel):
    artist: str
    title: str
    listen_url: str = ""


class QuoteAnswerOut(BaseModel):
    artist_ok: bool
    title_ok: bool
    fully_correct: bool
    points: int
    half_points: bool = False
    rarity: str = "commune"
    multiplier: float = 1.0
    message: str = ""
    reveal: QuoteReveal | None = None


class PartyAnswerIn(BaseModel):
    player_token: str = Field(min_length=8, max_length=80)
    quote_id: int
    artist: str = Field(default="", max_length=120)
    title: str = Field(default="", max_length=120)
    hints_used: int = Field(default=0, ge=0, le=10)


class PartySkipIn(BaseModel):
    player_token: str = Field(min_length=8, max_length=80)
    quote_id: int


# --- Lot F : contenu communautaire (MR-16 propositions, MR-17 votes) --------


class SubmissionIn(BaseModel):
    """Proposition d'une punchline par un joueur (`/proposer`)."""

    quote: str = Field(min_length=10, max_length=300)
    artist: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    category_id: int
    year: int | None = Field(default=None, ge=1900, le=2100)
    listen_url: str | None = Field(default=None, max_length=500)
    player_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    pseudo: str = Field(default="", max_length=200)


class SubmissionOut(BaseModel):
    id: int
    quote: str
    artist: str
    title: str
    category_id: int | None = None
    year: str = ""
    listen_url: str = ""
    player_id: str
    pseudo: str = ""
    status: str
    reason: str = ""
    quote_id: int | None = None
    created_at: str = ""
    reviewed_at: str | None = None


class SubmissionCreatedOut(BaseModel):
    id: int
    status: str
    message: str


class SubmissionListOut(BaseModel):
    items: list[SubmissionOut]
    counts: dict[str, int]


class SubmissionApproveIn(BaseModel):
    rarity: str | None = Field(default=None, pattern="^(commune|rare|legendaire)$")


class SubmissionRejectIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class PlayerRewardsOut(BaseModel):
    player_id: str
    points: int = 0
    badges: list[str] = Field(default_factory=list)


class SubmissionApproveOut(BaseModel):
    submission: SubmissionOut
    quote: QuoteOut
    rewards: PlayerRewardsOut


class QuoteVoteIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    value: int = Field(description="1 = 🔥, -1 = 👎")


class QuoteVoteOut(BaseModel):
    quote_id: int
    my_vote: int
    up: int
    down: int
    total: int


class FlaggedQuoteOut(BaseModel):
    id: int
    quote: str
    artist: str
    title: str
    rarity: str = "commune"
    contributor_pseudo: str = ""
    up: int
    down: int
    total: int
    down_ratio: float


# --- MR-08 / MR-14 : Web Push ---------------------------------------------


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=16, max_length=256)
    auth: str = Field(min_length=8, max_length=128)


class PushSubscription(BaseModel):
    endpoint: str = Field(min_length=16, max_length=2048, pattern=r"^https://")
    keys: PushKeys
    expirationTime: int | float | None = None


class PushSubscribeIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    subscription: PushSubscription
    tz: str = Field(default="America/Toronto", max_length=64)
    streak: int | None = Field(default=None, ge=0, le=100_000, description="Série connue du client (optionnel)")


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(min_length=16, max_length=2048)


class PushSubscribeOut(BaseModel):
    ok: bool
    id: int
    tz: str
    enabled: bool


class PushPublicKeyOut(BaseModel):
    enabled: bool
    public_key: str
    reminder_hour: int
