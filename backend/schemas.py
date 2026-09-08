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
    category_ids: list[int] = Field(default_factory=list)


class QuoteCreate(BaseModel):
    quote: str = Field(min_length=3)
    artist: str = Field(min_length=1)
    title: str = Field(min_length=1)
    hints: Hints | None = None
    category_ids: list[int] = Field(default_factory=list)


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
    player_token: str
    score: int = Field(ge=0)
    finished: bool = False
    progress: int | None = Field(default=None, ge=0, description="Index 1-based de la punchline en cours")
