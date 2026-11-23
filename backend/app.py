import os
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="RealShot API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"


def _with_referral(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update({"utm_source": "realshot", "utm_medium": "referral"})
    return urlunsplit(parts._replace(query=urlencode(query)))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RealShot"}


@app.get("/api/photos")
def search_photos(
    query: str = Query(min_length=2, max_length=180),
    limit: int = 20,
    orientation: Literal["all", "horizontal", "vertical"] = "all",
):
    if limit not in (20, 30, 40):
        raise HTTPException(
            status_code=400,
            detail="Le nombre de résultats doit être 20, 30 ou 40.",
        )

    if not UNSPLASH_ACCESS_KEY:
        raise HTTPException(
            status_code=503,
            detail="Clé Unsplash absente. Ajoute UNSPLASH_ACCESS_KEY dans backend/.env.",
        )

    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "Accept-Version": "v1",
    }
    per_page = min(limit, 30)
    page_count = (limit + per_page - 1) // per_page
    api_orientation = {
        "all": None,
        "horizontal": "landscape",
        "vertical": "portrait",
    }[orientation]
    results = []
    total = 0

    try:
        for page in range(1, page_count + 1):
            page_limit = min(per_page, limit - len(results))
            params = {
                "query": query.strip(),
                "per_page": page_limit,
                "page": page,
            }
            if api_orientation:
                params["orientation"] = api_orientation

            response = requests.get(
                UNSPLASH_API_URL,
                headers=headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            total = data.get("total", total)
            results.extend(data.get("results", []))
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Unsplash met trop de temps à répondre.")
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else None
        if status == 429:
            raise HTTPException(
                status_code=429,
                detail="Limite de requêtes Unsplash atteinte. Réessaie plus tard.",
            )
        if status in (401, 403):
            raise HTTPException(
                status_code=502,
                detail="Accès Unsplash refusé. Vérifie la clé et les droits de ton application.",
            )
        raise HTTPException(status_code=502, detail="Unsplash a refusé la recherche.")
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Impossible de contacter Unsplash.")
    except ValueError:
        raise HTTPException(status_code=502, detail="Unsplash a renvoyé une réponse invalide.")

    photos = []
    for item in results:
        urls = item.get("urls") or {}
        links = item.get("links") or {}
        user = item.get("user") or {}
        user_links = user.get("links") or {}
        preview_url = urls.get("small")
        image_url = urls.get("regular") or preview_url
        source_url = links.get("html")
        photographer_url = user_links.get("html")

        if not item.get("id") or not preview_url or not image_url or not source_url:
            continue

        photos.append(
            {
                "id": item["id"],
                "preview_url": preview_url,
                "image_url": image_url,
                "source_url": _with_referral(source_url),
                "photographer": user.get("name") or "Photographe Unsplash",
                "photographer_url": (
                    _with_referral(photographer_url) if photographer_url else None
                ),
                "tags": item.get("alt_description") or item.get("description") or query,
                "width": item.get("width", 0),
                "height": item.get("height", 0),
            }
        )

    return {
        "query": query.strip(),
        "total": total,
        "photos": photos,
    }
