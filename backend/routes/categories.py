import re

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin
from db import (
    add_quotes_to_category,
    create_category,
    delete_category,
    get_category,
    get_db,
    list_categories,
    list_quotes,
    remove_quote_from_category,
)
from schemas import CategoryAssign, CategoryCreate, CategoryOut, QuoteOut

router = APIRouter(prefix="/api/music-refs/categories", tags=["categories"])


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[àâä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[îï]", "i", s)
    s = re.sub(r"[ôö]", "o", s)
    s = re.sub(r"[ùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "categorie"


@router.get("", response_model=list[CategoryOut])
def get_categories() -> list[CategoryOut]:
    with get_db() as conn:
        return [CategoryOut(**c) for c in list_categories(conn)]


@router.get("/{category_id}", response_model=CategoryOut)
def get_one_category(category_id: int) -> CategoryOut:
    with get_db() as conn:
        c = get_category(conn, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut(**c)


@router.get("/{category_id}/quotes", response_model=list[QuoteOut])
def get_category_quotes(category_id: int) -> list[QuoteOut]:
    with get_db() as conn:
        if not get_category(conn, category_id):
            raise HTTPException(status_code=404, detail="Category not found")
        return [QuoteOut(**q) for q in list_quotes(conn, category_id)]


@router.post("", response_model=CategoryOut, dependencies=[Depends(require_admin)])
def post_category(body: CategoryCreate) -> CategoryOut:
    slug = (body.slug or _slugify(body.name)).strip().lower()
    try:
        with get_db() as conn:
            c = create_category(conn, name=body.name, slug=slug, description=body.description)
        return CategoryOut(**c)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot create category: {exc}") from exc


@router.delete("/{category_id}", dependencies=[Depends(require_admin)])
def remove_category(category_id: int) -> dict:
    with get_db() as conn:
        ok = delete_category(conn, category_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True, "deleted": category_id}


@router.post("/{category_id}/quotes", dependencies=[Depends(require_admin)])
def assign_quotes(category_id: int, body: CategoryAssign) -> dict:
    with get_db() as conn:
        n = add_quotes_to_category(conn, category_id, body.quote_ids)
    if n < 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True, "assigned": n, "category_id": category_id}


@router.delete("/{category_id}/quotes/{quote_id}", dependencies=[Depends(require_admin)])
def unassign_quote(category_id: int, quote_id: int) -> dict:
    with get_db() as conn:
        ok = remove_quote_from_category(conn, category_id, quote_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"ok": True}
