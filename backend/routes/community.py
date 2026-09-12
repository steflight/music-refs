"""Lot F — contenu communautaire.

MR-16 : proposer une punchline (`POST /submissions`, statut `pending`), relue en
admin (`GET /submissions`, `POST /submissions/{id}/approve|reject`) ; à
l'approbation la citation entre dans `quotes` avec le pseudo du contributeur,
qui reçoit +50 points et le badge « contributeur » (`GET /players/{id}/rewards`).

MR-17 : vote 🔥 / 👎 (`POST /quotes/{id}/vote`) réservé aux joueurs ayant
répondu à la citation (présence dans `daily_answers`) ; un seul vote par joueur
et par citation, revotable. `GET /quotes/flagged` (admin) liste les citations
avec ≥ 30 votes et plus de 40 % de 👎.

NB : ce routeur doit être inclus AVANT `routes.quotes` dans main.py, sinon
`GET /quotes/flagged` est capté par `GET /quotes/{quote_id}`.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin
from daily import normalize_answer, today_toronto
from db import (
    CONTRIBUTOR_BADGE,
    CONTRIBUTOR_POINTS,
    SUBMISSION_STATUSES,
    count_submissions_by_status,
    count_submissions_for_day,
    credit_player_reward,
    find_duplicate_submission,
    get_category,
    get_db,
    get_player_rewards,
    get_player_vote,
    get_quote,
    get_submission,
    insert_quote,
    insert_submission,
    iter_quote_identities,
    list_flagged_quotes,
    list_submissions,
    player_has_played_quote,
    quote_vote_counts,
    set_quote_contributor,
    set_submission_status,
    upsert_quote_vote,
)
from moderation import validate_pseudo
from schemas import (
    FlaggedQuoteOut,
    PlayerRewardsOut,
    QuoteOut,
    QuoteVoteIn,
    QuoteVoteOut,
    SubmissionApproveIn,
    SubmissionApproveOut,
    SubmissionCreatedOut,
    SubmissionIn,
    SubmissionListOut,
    SubmissionOut,
    SubmissionRejectIn,
)

router = APIRouter(prefix="/api/music-refs", tags=["community"])

SUBMISSIONS_PER_DAY = 10
YEAR_MIN = 1900

# Hôtes acceptés pour le lien d'écoute (suffixes, comparés en minuscules).
ALLOWED_LISTEN_HOSTS = (
    "spotify.com",
    "spotify.link",
    "youtube.com",
    "youtu.be",
    "deezer.com",
    "deezer.page.link",
    "music.apple.com",
    "itunes.apple.com",
)

MSG_DUPLICATE = "Cette punchline existe déjà"
MSG_DAILY_LIMIT = f"Tu as atteint la limite de {SUBMISSIONS_PER_DAY} propositions par jour. Reviens demain !"
MSG_BAD_URL = "Lien d'écoute non accepté : uniquement une adresse http(s) Spotify, YouTube, Deezer ou Apple Music"
MSG_BAD_YEAR = f"L'année doit être comprise entre {YEAR_MIN} et l'année en cours"
MSG_PSEUDO_REQUIRED = "Choisis un pseudo pour signer ta proposition"
MSG_CATEGORY = "Catégorie introuvable"
MSG_QUOTE_NOT_FOUND = "Citation introuvable"
MSG_SUBMISSION_NOT_FOUND = "Proposition introuvable"
MSG_ALREADY_REVIEWED = "Cette proposition a déjà été traitée"
MSG_VOTE_FORBIDDEN = "Réponds d'abord à cette citation"
MSG_VOTE_VALUE = "Le vote doit valoir 1 (🔥) ou -1 (👎)"
MSG_SUBMITTED = "Merci ! Ta ref sera relue avant d'entrer dans le jeu."


def listen_url_allowed(url: str) -> bool:
    """URL http(s) dont l'hôte est (ou termine par) un domaine d'écoute connu."""
    raw = (url or "").strip()
    if not raw:
        return True
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_LISTEN_HOSTS)


def _pseudo_or_422(raw: str | None) -> str:
    try:
        return validate_pseudo(raw)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


def _catalogue_has_duplicate(conn, artist_norm: str, quote_norm: str) -> bool:
    for _qid, artist, quote in iter_quote_identities(conn):
        if normalize_answer(artist) == artist_norm and normalize_answer(quote) == quote_norm:
            return True
    return False


# --- MR-16 : proposer -------------------------------------------------------


@router.post("/submissions", response_model=SubmissionCreatedOut, status_code=status.HTTP_201_CREATED)
def create_submission(body: SubmissionIn):
    """Dépose une proposition en statut `pending`. 409 si doublon évident
    (même artiste + même texte normalisés) dans le catalogue ou les propositions
    non rejetées ; 429 au-delà de 10 propositions par joueur et par jour."""
    pseudo = _pseudo_or_422(body.pseudo)
    if not pseudo:
        raise HTTPException(422, MSG_PSEUDO_REQUIRED)
    if body.year is not None and not (YEAR_MIN <= body.year <= date.today().year):
        raise HTTPException(422, MSG_BAD_YEAR)
    listen_url = (body.listen_url or "").strip()
    if not listen_url_allowed(listen_url):
        raise HTTPException(422, MSG_BAD_URL)
    quote = " ".join(body.quote.split())
    artist = " ".join(body.artist.split())
    title = " ".join(body.title.split())
    if len(quote) < 10:
        raise HTTPException(422, "La citation doit faire au moins 10 caractères")
    if not artist or not title:
        raise HTTPException(422, "Artiste et titre sont requis")
    quote_norm = normalize_answer(quote)
    artist_norm = normalize_answer(artist)
    if not quote_norm or not artist_norm:
        raise HTTPException(422, "Citation ou artiste illisible")

    today = today_toronto().isoformat()
    with get_db() as conn:
        if not get_category(conn, body.category_id):
            raise HTTPException(422, MSG_CATEGORY)
        if count_submissions_for_day(conn, body.player_id, today) >= SUBMISSIONS_PER_DAY:
            raise HTTPException(429, MSG_DAILY_LIMIT)
        if _catalogue_has_duplicate(conn, artist_norm, quote_norm) or find_duplicate_submission(
            conn, artist_norm, quote_norm
        ):
            raise HTTPException(409, MSG_DUPLICATE)
        sub = insert_submission(
            conn,
            quote=quote,
            artist=artist,
            title=title,
            category_id=body.category_id,
            year=str(body.year) if body.year else "",
            listen_url=listen_url,
            player_id=body.player_id,
            pseudo=pseudo,
            quote_norm=quote_norm,
            artist_norm=artist_norm,
            created_day=today,
        )
    return SubmissionCreatedOut(id=sub["id"], status=sub["status"], message=MSG_SUBMITTED)


# --- MR-16 : relecture admin ------------------------------------------------


@router.get("/submissions", response_model=SubmissionListOut, dependencies=[Depends(require_admin)])
def admin_list_submissions(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    with get_db() as conn:
        items = list_submissions(conn, status_filter, limit)
        counts = count_submissions_by_status(conn)
    return SubmissionListOut(items=[SubmissionOut(**s) for s in items], counts=counts)


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=SubmissionApproveOut,
    dependencies=[Depends(require_admin)],
)
def admin_approve_submission(submission_id: int, body: SubmissionApproveIn | None = None):
    """Crée la citation (lien d'écoute, année, catégorie, pseudo du contributeur),
    marque la proposition `approved` et crédite +50 points + badge « contributeur »."""
    with get_db() as conn:
        sub = get_submission(conn, submission_id)
        if not sub:
            raise HTTPException(404, MSG_SUBMISSION_NOT_FOUND)
        if sub["status"] != "pending":
            raise HTTPException(409, MSG_ALREADY_REVIEWED)
        cat = get_category(conn, sub["category_id"]) if sub["category_id"] else None
        q = insert_quote(
            conn,
            quote=sub["quote"],
            artist=sub["artist"],
            title=sub["title"],
            year=sub["year"] or "",
            genre=cat["name"] if cat else "",
            listen_url=sub["listen_url"] or "",
            rarity=(body.rarity if body and body.rarity else "commune"),
            category_ids=[cat["id"]] if cat else [],
        )
        set_quote_contributor(conn, q["id"], contributor_pseudo=sub["pseudo"], submission_id=sub["id"])
        updated = set_submission_status(conn, sub["id"], status="approved", quote_id=q["id"])
        rewards = credit_player_reward(conn, sub["player_id"], points=CONTRIBUTOR_POINTS, badge=CONTRIBUTOR_BADGE)
        quote = get_quote(conn, q["id"])
    return SubmissionApproveOut(
        submission=SubmissionOut(**updated),  # type: ignore[arg-type]
        quote=QuoteOut(**{**quote, "category_ids": quote.get("category_ids") or []}),  # type: ignore[union-attr]
        rewards=PlayerRewardsOut(**rewards),
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=SubmissionOut,
    dependencies=[Depends(require_admin)],
)
def admin_reject_submission(submission_id: int, body: SubmissionRejectIn | None = None):
    with get_db() as conn:
        sub = get_submission(conn, submission_id)
        if not sub:
            raise HTTPException(404, MSG_SUBMISSION_NOT_FOUND)
        if sub["status"] != "pending":
            raise HTTPException(409, MSG_ALREADY_REVIEWED)
        updated = set_submission_status(conn, sub["id"], status="rejected", reason=(body.reason if body else ""))
    return SubmissionOut(**updated)  # type: ignore[arg-type]


# --- MR-16 : récompenses ----------------------------------------------------


@router.get("/players/{player_id}/rewards", response_model=PlayerRewardsOut)
def player_rewards(player_id: str):
    """Public : points et badges du joueur (affichable par le profil)."""
    if not (8 <= len(player_id) <= 64):
        raise HTTPException(422, "player_id invalide")
    with get_db() as conn:
        return PlayerRewardsOut(**get_player_rewards(conn, player_id))


# --- MR-17 : vote -----------------------------------------------------------


@router.get("/quotes/flagged", response_model=list[FlaggedQuoteOut], dependencies=[Depends(require_admin)])
def admin_flagged_quotes():
    """Citations à ≥ 30 votes dont plus de 40 % de 👎 (MR-17)."""
    with get_db() as conn:
        return [FlaggedQuoteOut(**row) for row in list_flagged_quotes(conn)]


@router.post("/quotes/{quote_id}/vote", response_model=QuoteVoteOut)
def vote_quote(quote_id: int, body: QuoteVoteIn):
    """Un vote par joueur et par citation (revotable). 403 tant que le joueur
    n'a pas répondu à cette citation (aucune ligne dans `daily_answers`)."""
    if body.value not in (1, -1):
        raise HTTPException(422, MSG_VOTE_VALUE)
    with get_db() as conn:
        if not get_quote(conn, quote_id):
            raise HTTPException(404, MSG_QUOTE_NOT_FOUND)
        if not player_has_played_quote(conn, body.player_id, quote_id):
            raise HTTPException(403, MSG_VOTE_FORBIDDEN)
        upsert_quote_vote(conn, quote_id, body.player_id, body.value)
        counts = quote_vote_counts(conn, quote_id)
        mine = get_player_vote(conn, quote_id, body.player_id)
    return QuoteVoteOut(quote_id=quote_id, my_vote=int(mine or 0), **counts)


__all__ = ["router", "listen_url_allowed", "SUBMISSIONS_PER_DAY", "SUBMISSION_STATUSES"]
