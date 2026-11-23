# RealShot — Résumé du projet et plan d’implémentation

**Date :** 23 novembre 2026  
**Objectif :** créer un site web gratuit de recherche de photos réalistes et spontanées, avec téléchargement individuel lorsque le fournisseur l’autorise.

---

## 1. Vision du projet

RealShot est une application web qui permet à l’utilisateur de saisir une description, par exemple :

- `morning coffee`
- `young woman reading book candid home photography`
- `everyday life candid photography unposed`
- `friends walking street candid lifestyle photography`
- `natural portrait woman imperfect lighting`

Le site recherche des photos lifestyle naturelles, affiche une galerie, permet de sélectionner des images et ouvre la page officielle de chaque image pour consulter les conditions de téléchargement.

### Objectif de la première version (MVP)

- Recherche par mots-clés.
- Choix de 20, 30 ou 40 résultats.
- Filtre d’orientation : portrait, paysage ou toutes.
- Galerie de photos avec aperçu.
- Affichage du photographe et des informations de source.
- Sélection de photos.
- Accès à la page d’origine de chaque photo pour la télécharger selon les règles du fournisseur.
- Fonctionnement local sans compte utilisateur ni base de données.

## 2. Technologies choisies

### Frontend

- **Next.js**
- **TypeScript**
- **Tailwind CSS**

Responsabilités :
- Interface de recherche.
- Filtres et choix du nombre de résultats.
- Galerie responsive.
- Sélection des photos.
- États de chargement et messages d’erreur.
- Liens vers les pages d’origine des images.

### Backend

- **Python**
- **FastAPI**
- **Uvicorn**
- **Requests**
- **python-dotenv**

Responsabilités :
- Recevoir et valider les recherches.
- Appeler l’API du fournisseur d’images.
- Limiter le nombre de résultats à 40.
- Normaliser les données renvoyées au frontend.
- Garder la clé API secrète.
- Gérer les erreurs réseau et les paramètres invalides.

### Source d’images prévue

**Source principale envisagée : Pixabay API.**

Documentation :
- https://pixabay.com/api/docs/
- https://pixabay.com/
- Licence : https://pixabay.com/service/license-summary/

L’accès à une clé API doit être vérifié au moment de l’implémentation. Si l’inscription ou l’accès API n’est pas disponible, ne pas contourner les protections du fournisseur.

### Solution de secours sans clé API

Ouvrir la recherche publique Pixabay dans le navigateur :
`https://pixabay.com/images/search/`

Le site peut construire une URL de recherche à partir des mots-clés et laisser l’utilisateur consulter les résultats manuellement. Ne pas scraper automatiquement les pages ni contourner les protections.

## 3. Architecture générale

```text
realshot/
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx
│   │       ├── layout.tsx
│   │       └── globals.css
│   ├── .env.local
│   └── package.json
│
├── backend/
│   ├── app.py
│   ├── .env
│   ├── .gitignore
│   └── requirements.txt
│
├── .gitignore
└── README.md
```

Architecture logique :

```text
Utilisateur
   |
   v
Frontend Next.js
   |
   | requête HTTP locale
   v
Backend FastAPI
   |
   | clé API gardée côté serveur
   v
API du fournisseur d’images
   |
   v
Résultats normalisés
   |
   v
Galerie Next.js
   |
   v
Page officielle de l’image / téléchargement autorisé
```

## 4. Préparer l’environnement Windows

Vérifier les outils dans PowerShell :

```powershell
node --version
npm --version
python --version
```

Créer le frontend :

```powershell
mkdir realshot
cd realshot

npx create-next-app@latest frontend --typescript --eslint --app --src-dir --use-npm
```

Créer le backend et son environnement Python :

```powershell
mkdir backend
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install fastapi "uvicorn[standard]" requests python-dotenv
```

Si PowerShell empêche l’activation de l’environnement virtuel :

```powershell
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" requests python-dotenv
```

## 5. Backend FastAPI — prototype

Fichier : `backend/app.py`

```python
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="RealShot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RealShot"}


@app.get("/api/photos")
def search_photos(
    query: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=20, le=40),
    orientation: str = Query(default="all"),
):
    if not PIXABAY_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Clé API absente. Utilisez la recherche manuelle."
        )

    if orientation not in ["all", "horizontal", "vertical"]:
        raise HTTPException(
            status_code=400,
            detail="Orientation invalide."
        )

    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "image_type": "photo",
        "orientation": orientation,
        "safesearch": "true",
        "per_page": limit,
        "page": 1,
        "lang": "en",
    }

    try:
        response = requests.get(
            "https://pixabay.com/api/",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Impossible de contacter Pixabay."
        )

    photos = []

    for item in data.get("hits", []):
        photos.append({
            "id": item["id"],
            "preview_url": item["previewURL"],
            "source_url": item["pageURL"],
            "photographer": item["user"],
            "tags": item["tags"],
            "width": item["imageWidth"],
            "height": item["imageHeight"],
        })

    return {
        "query": query,
        "total": data.get("totalHits", 0),
        "photos": photos,
    }
```

### Variables d’environnement

Fichier : `backend/.env`

```dotenv
PIXABAY_API_KEY=
```

Laisser la valeur vide jusqu’à l’obtention d’une clé valide.

Fichier : `backend/.gitignore`

```gitignore
.env
.venv/
__pycache__/
*.pyc
```

Ne jamais publier la clé API sur GitHub ni l’exposer dans une variable frontend `NEXT_PUBLIC_*`.

### Lancer le backend

Depuis le dossier `backend` :

```powershell
python -m uvicorn app:app --reload --port 8000
```

Vérifier :
- Santé : http://localhost:8000/api/health
- Documentation interactive : http://localhost:8000/docs

## 6. Frontend Next.js — prototype

Fichier : `frontend/src/app/page.tsx`

```tsx
"use client";

import { useState } from "react";

type Photo = {
  id: number;
  preview_url: string;
  source_url: string;
  photographer: string;
  tags: string;
  width: number;
  height: number;
};

const API_URL = "http://localhost:8000";

export default function Home() {
  const [query, setQuery] = useState("morning coffee");
  const [limit, setLimit] = useState(20);
  const [orientation, setOrientation] = useState("vertical");
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function searchPhotos() {
    if (query.trim().length < 2) {
      setError("Écris au moins deux caractères.");
      return;
    }

    setLoading(true);
    setError("");
    setPhotos([]);
    setSelected([]);

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        limit: String(limit),
        orientation,
      });

      const response = await fetch(
        `${API_URL}/api/photos?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error("API indisponible");
      }

      const data = await response.json();
      setPhotos(data.photos);

      if (data.photos.length === 0) {
        setError("Aucune photo trouvée. Essaie d'autres mots-clés.");
      }
    } catch {
      setError(
        "API indisponible ou clé absente. Tu peux continuer sur Pixabay."
      );
    } finally {
      setLoading(false);
    }
  }

  function togglePhoto(id: number) {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((photoId) => photoId !== id)
        : [...current, id]
    );
  }

  const fallbackUrl =
    "https://pixabay.com/images/search/" +
    encodeURIComponent(query.trim()) +
    "/";

  return (
    <main className="min-h-screen bg-stone-950 px-5 py-10 text-white md:px-12">
      <header className="mx-auto mb-12 max-w-6xl">
        <p className="mb-3 text-sm uppercase tracking-[0.3em] text-emerald-400">
          REALSHOT · LIFESTYLE SEARCH
        </p>

        <h1 className="text-4xl font-bold md:text-6xl">
          Real moments.
          <span className="block text-stone-400">
            Natural photography.
          </span>
        </h1>

        <p className="mt-5 max-w-xl text-stone-400">
          Trouve des photos spontanées, sélectionne tes préférées
          et ouvre leur page source pour les télécharger.
        </p>
      </header>

      <section className="mx-auto max-w-6xl">
        <form
          className="grid gap-4 rounded-2xl border border-stone-800 bg-stone-900 p-5 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            searchPhotos();
          }}
        >
          <label className="md:col-span-2">
            <span className="mb-2 block text-sm text-stone-400">
              Description
            </span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="morning coffee, candid lifestyle..."
              className="w-full rounded-xl border border-stone-700 bg-stone-950 px-4 py-3 outline-none focus:border-emerald-500"
            />
          </label>

          <label>
            <span className="mb-2 block text-sm text-stone-400">
              Nombre de photos
            </span>
            <select
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
              className="w-full rounded-xl border border-stone-700 bg-stone-950 px-4 py-3"
            >
              <option value={20}>20 photos</option>
              <option value={30}>30 photos</option>
              <option value={40}>40 photos</option>
            </select>
          </label>

          <label>
            <span className="mb-2 block text-sm text-stone-400">
              Orientation
            </span>
            <select
              value={orientation}
              onChange={(event) => setOrientation(event.target.value)}
              className="w-full rounded-xl border border-stone-700 bg-stone-950 px-4 py-3"
            >
              <option value="vertical">Portrait</option>
              <option value="horizontal">Paysage</option>
              <option value="all">Toutes</option>
            </select>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-emerald-500 px-5 py-3 font-semibold text-stone-950 hover:bg-emerald-400 disabled:opacity-50 md:col-span-4"
          >
            {loading ? "Recherche..." : "Rechercher des photos"}
          </button>
        </form>

        {error && (
          <div className="mt-5 rounded-xl border border-stone-700 bg-stone-900 p-5">
            <p className="mb-3 text-stone-300">{error}</p>
            <a
              href={fallbackUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block rounded-lg bg-white px-4 py-2 font-medium text-black"
            >
              Rechercher directement sur Pixabay ↗
            </a>
          </div>
        )}

        <div className="my-8 flex flex-wrap items-center justify-between gap-3">
          <p className="text-stone-400">
            {photos.length} résultat(s) · {selected.length} sélectionnée(s)
          </p>

          {selected.length > 0 && (
            <button
              onClick={() => {
                const photo = photos.find(
                  (item) => item.id === selected[0]
                );

                if (photo) {
                  window.open(
                    photo.source_url,
                    "_blank",
                    "noopener,noreferrer"
                  );
                }
              }}
              className="rounded-lg border border-emerald-500 px-4 py-2 text-emerald-400"
            >
              Ouvrir une photo sélectionnée ↗
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {photos.map((photo) => (
            <article
              key={photo.id}
              className="overflow-hidden rounded-xl border border-stone-800 bg-stone-900"
            >
              <a
                href={photo.source_url}
                target="_blank"
                rel="noopener noreferrer"
                title="Voir la photo sur Pixabay"
              >
                <img
                  src={photo.preview_url}
                  alt={photo.tags}
                  loading="lazy"
                  className="h-64 w-full object-cover transition hover:scale-[1.02]"
                />
              </a>

              <div className="space-y-3 p-3">
                <p className="truncate text-sm text-stone-400">
                  Photo : {photo.photographer}
                </p>

                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.includes(photo.id)}
                    onChange={() => togglePhoto(photo.id)}
                    className="accent-emerald-500"
                  />
                  Sélectionner
                </label>

                <a
                  href={photo.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-lg bg-stone-800 px-3 py-2 text-center text-sm hover:bg-stone-700"
                >
                  Voir / télécharger ↗
                </a>
              </div>
            </article>
          ))}
        </div>
      </section>

      <footer className="mx-auto mt-16 max-w-6xl text-sm text-stone-500">
        Images fournies par Pixabay. Vérifie les conditions de licence
        avant chaque réutilisation.
      </footer>
    </main>
  );
}
```

## 7. Déroulement des tests

Garder deux terminaux ouverts.

**Terminal 1 — Backend :**

```powershell
cd realshot\backend
python -m uvicorn app:app --reload --port 8000
```

**Terminal 2 — Frontend :**

```powershell
cd realshot\frontend
npm run dev
```

Puis ouvrir http://localhost:3000.

| Test | Résultat attendu |
|---|---|
| Backend disponible | `/api/health` renvoie `status: ok` |
| Clé absente | Le frontend affiche un message et le lien de recherche manuelle |
| Clé valide | La galerie affiche les photos trouvées |
| Aucun résultat | Le site invite à modifier les mots-clés |
| Téléchargement | La page source officielle s'ouvre |

## 8. Plan d'amélioration

- [ ] Vérifier l'accès effectif à l'API Pixabay.
- [ ] Tester la recherche avec 20 résultats.
- [ ] Affiner les prompts pour favoriser les photos spontanées.
- [ ] Ajouter une vraie sélection multiple et une navigation entre pages de résultats.
- [ ] Ajouter un cache de 24 heures conforme aux règles du fournisseur.
- [ ] Ajouter une seconde source d'images autorisée si nécessaire.
- [ ] Tester les licences et les conditions de téléchargement.
- [ ] Déployer seulement après validation locale.

## 9. Budget estimé

| Élément | Coût initial |
|---|---:|
| Next.js et FastAPI | Gratuit |
| Développement local | Gratuit |
| Base de données | Non nécessaire au MVP |
| API d'images | Gratuit si accès accordé et dans les limites |
| Domaine personnalisé | Facultatif |
| Hébergement | Offre gratuite possible selon les limites |

## 10. Liens utiles

- Next.js : https://nextjs.org/docs
- FastAPI : https://fastapi.tiangolo.com/
- Pixabay API : https://pixabay.com/api/docs/
- Licence Pixabay : https://pixabay.com/service/license-summary/
- Recherche manuelle Pixabay : https://pixabay.com/images/search/
- Variables d’environnement Next.js : https://nextjs.org/docs/app/guides/environment-variables

---

## Note importante

Le code fourni est un **prototype de départ**, pas encore une application de production. La clé API doit rester secrète, les règles de cache et de téléchargement du fournisseur doivent être respectées, et l’ouverture de la page source est utilisée plutôt qu'un téléchargement automatisé massif. Vérifier les conditions actuelles du fournisseur avant le déploiement.
