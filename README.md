# FastAPI Blog

Application de blog full-stack avec une API backend asynchrone en **FastAPI** et une interface utilisateur en **React (Vite)**.

## Sommaire

- [Aperçu](#aperçu)
- [Stack technique](#stack-technique)
- [Structure du projet](#structure-du-projet)
- [Prérequis](#prérequis)
- [Installation](#installation)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Variables d'environnement](#variables-denvironnement)
- [Lancer le projet](#lancer-le-projet)
- [Endpoints de l'API](#endpoints-de-lapi)
- [Documentation interactive](#documentation-interactive)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Auteur](#auteur)

## Aperçu

Plateforme de blog permettant aux utilisateurs de créer, consulter, modifier et supprimer des articles. Le backend expose une API REST asynchrone et un rendu HTML via Jinja2, tandis que le frontend React communique avec l'API.

- **backend/** : API REST asynchrone développée avec FastAPI + SQLAlchemy async
- **frontend/** : interface web développée avec React (Vite)

## Stack technique

**Backend**
- Python 3.13
- FastAPI
- SQLAlchemy 2.0 (mode asynchrone) + aiosqlite
- Pydantic v2 (validation et sérialisation des données)
- Jinja2 (rendu HTML côté serveur)
- [uv](https://docs.astral.sh/uv/) (gestion des dépendances et environnement virtuel)

**Frontend**
- React (Vite)
- JavaScript / JSX

**Tests**
- pytest + pytest-asyncio
- httpx (AsyncClient)

## Structure du projet

```
fastapi_blog/
├── backend/
│   ├── routes/
│   │   ├── posts.py          ← Endpoints API + pages HTML des articles
│   │   ├── users.py          ← Endpoints API + pages HTML des utilisateurs
│   │   └── __init__.py
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   ├── js/
│   │   │   └── utils.js
│   │   └── icons/
│   ├── media/
│   │   └── profile_pics/     ← Photos de profil uploadées (ignorées par Git)
│   ├── templates/
│   │   ├── layout.html       ← Template de base (héritage Jinja2)
│   │   ├── home.html
│   │   ├── post.html
│   │   ├── user_posts.html
│   │   └── error.html
│   ├── main.py               ← Application FastAPI, lifespan, error handlers
│   ├── database.py           ← Configuration SQLAlchemy async
│   ├── models.py             ← Modèles ORM (User, Post)
│   ├── schema.py             ← Schémas Pydantic (Create, Response, Update)
│   ├── test_main.py          ← Tests automatisés (pytest)
│   ├── pytest.ini
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── .gitignore
└── README.md
```

## Prérequis

- [Python 3.10+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js 18+](https://nodejs.org/) et npm
- Git

## Installation

### Backend

```bash
cd backend
uv sync
```

`uv sync` installe automatiquement toutes les dépendances depuis `pyproject.toml` et crée l'environnement virtuel.

### Frontend

```bash
cd frontend
npm install
```

## Variables d'environnement

Crée un fichier `.env` dans `backend/` (inspire-toi de `.env.example`) :

```
DATABASE_URL=sqlite+aiosqlite:///./blog.db
```

Crée un fichier `.env` dans `frontend/` :

```
VITE_API_URL=http://localhost:8000
```

## Lancer le projet

**Backend** (depuis le dossier `backend/`) :

```bash
fastapi dev main.py
```

L'API sera disponible sur `http://localhost:8000`

**Frontend** (depuis le dossier `frontend/`) :

```bash
npm run dev
```

L'application sera disponible sur `http://localhost:5173`

## Endpoints de l'API

### Articles (Posts)

| Méthode  | Endpoint           | Description                        |
|----------|--------------------|------------------------------------|
| `GET`    | `/api/posts`       | Lister tous les articles           |
| `POST`   | `/api/posts`       | Créer un nouvel article            |
| `GET`    | `/api/posts/{id}`  | Récupérer un article par son ID    |
| `PUT`    | `/api/posts/{id}`  | Mise à jour complète d'un article  |
| `PATCH`  | `/api/posts/{id}`  | Mise à jour partielle d'un article |
| `DELETE` | `/api/posts/{id}`  | Supprimer un article               |

### Utilisateurs (Users)

| Méthode  | Endpoint                | Description                           |
|----------|-------------------------|---------------------------------------|
| `POST`   | `/api/users`            | Créer un nouvel utilisateur           |
| `GET`    | `/api/users/{id}`       | Récupérer un utilisateur par son ID   |
| `PUT`    | `/api/users/{id}`       | Mise à jour complète d'un utilisateur |
| `DELETE` | `/api/users/{id}`       | Supprimer un utilisateur              |
| `GET`    | `/api/users/{id}/posts` | Lister les articles d'un utilisateur  |

### Pages HTML

| Route                | Description                         |
|----------------------|-------------------------------------|
| `/`                  | Page d'accueil — liste des articles |
| `/posts`             | Alias de la page d'accueil          |
| `/posts/{id}`        | Page de détail d'un article         |
| `/users/{id}/posts`  | Articles d'un utilisateur           |

## Documentation interactive

FastAPI génère automatiquement une documentation de l'API :

- Swagger UI : `http://localhost:8000/docs`
- Redoc : `http://localhost:8000/redoc`

## Tests

Les tests utilisent `pytest`, `pytest-asyncio` et `httpx` avec une base de données SQLite dédiée aux tests, entièrement isolée de la base de données principale.

```bash
cd backend
pytest test_main.py -v
```

## Roadmap

- [x] Structure du projet (backend + frontend)
- [x] Rendu HTML avec Jinja2 et fichiers statiques
- [x] Mode asynchrone (SQLAlchemy async + aiosqlite)
- [x] Schémas Pydantic v2 (validation et sérialisation)
- [x] CRUD complet — Articles (GET, POST, PUT, PATCH, DELETE)
- [x] CRUD complet — Utilisateurs (GET, POST, PUT, DELETE)
- [x] Découpage en routers (routes/posts.py, routes/users.py)
- [x] Gestion globale des erreurs (HTML et API)
- [x] Tests automatisés (pytest-asyncio + httpx)
- [ ] Hashage des mots de passe (passlib + bcrypt)
- [ ] Authentification JWT
- [ ] Protection des routes (get_current_user)
- [ ] Gestion des commentaires
- [ ] Upload d'images pour les articles
- [ ] Pagination et recherche
- [ ] Connexion avec le frontend React
- [ ] Déploiement

## Auteur

**Abdoul Aziz Baba**  
Développeur Fullstack — Douala, Cameroun