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

Plateforme de blog permettant aux utilisateurs de s'inscrire, se connecter, et créer, consulter, modifier ou supprimer des articles. Le backend expose une API REST asynchrone sécurisée par JWT et un rendu HTML via Jinja2.

- **backend/** : API REST asynchrone — FastAPI + SQLAlchemy async + authentification JWT
- **frontend/** : interface web — React (Vite)

## Stack technique

**Backend**
- Python 3.13
- FastAPI
- SQLAlchemy 2.0 (mode asynchrone) + aiosqlite
- Pydantic v2 + pydantic-settings (validation, sérialisation, configuration)
- pwdlib[argon2] (hashage des mots de passe)
- PyJWT (authentification par token JWT)
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
│   │   ├── posts.py          ← Endpoints API articles
│   │   ├── users.py          ← Endpoints API utilisateurs + auth (login, /me)
│   │   └── __init__.py
│   ├── static/
│   │   ├── css/main.css
│   │   ├── js/
│   │   │   ├── auth.js       ← Gestion de l'état d'authentification (JS)
│   │   │   └── utils.js
│   │   └── icons/
│   ├── media/
│   │   └── profile_pics/     ← Photos de profil uploadées (ignorées par Git)
│   ├── templates/
│   │   ├── layout.html       ← Template de base (navbar, modals globaux)
│   │   ├── home.html
│   │   ├── post.html
│   │   ├── user_posts.html
│   │   ├── login.html
│   │   ├── register.html
│   │   └── error.html
│   ├── main.py               ← Application FastAPI, lifespan, error handlers
│   ├── database.py           ← Configuration SQLAlchemy async
│   ├── models.py             ← Modèles ORM (User, Post)
│   ├── schema.py             ← Schémas Pydantic (Create, Response, Update, Token)
│   ├── auth.py               ← Utilitaires JWT et hashage (pwdlib + PyJWT)
│   ├── config.py             ← Configuration via pydantic-settings (.env)
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
SECRET_KEY=change_this_to_a_long_random_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
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

### Authentification

| Méthode | Endpoint          | Description                              |
|---------|-------------------|------------------------------------------|
| `POST`  | `/api/users/token`| Connexion — retourne un token JWT        |
| `GET`   | `/api/users/me`   | Récupère l'utilisateur connecté          |

### Utilisateurs (Users)

| Méthode  | Endpoint                | Description                           |
|----------|-------------------------|---------------------------------------|
| `POST`   | `/api/users`            | Créer un compte (inscription)         |
| `GET`    | `/api/users/{id}`       | Profil public d'un utilisateur        |
| `PUT`    | `/api/users/{id}`       | Mise à jour d'un utilisateur          |
| `DELETE` | `/api/users/{id}`       | Supprimer un utilisateur              |
| `GET`    | `/api/users/{id}/posts` | Articles d'un utilisateur             |

### Articles (Posts)

| Méthode  | Endpoint           | Description                        |
|----------|--------------------|------------------------------------|
| `GET`    | `/api/posts`       | Lister tous les articles           |
| `POST`   | `/api/posts`       | Créer un nouvel article            |
| `GET`    | `/api/posts/{id}`  | Récupérer un article par son ID    |
| `PUT`    | `/api/posts/{id}`  | Mise à jour complète d'un article  |
| `PATCH`  | `/api/posts/{id}`  | Mise à jour partielle d'un article |
| `DELETE` | `/api/posts/{id}`  | Supprimer un article               |

### Pages HTML

| Route                | Description                         |
|----------------------|-------------------------------------|
| `/`                  | Page d'accueil — liste des articles |
| `/posts`             | Alias de la page d'accueil          |
| `/posts/{id}`        | Page de détail d'un article         |
| `/users/{id}/posts`  | Articles d'un utilisateur           |
| `/login`             | Page de connexion                   |
| `/register`          | Page d'inscription                  |

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
- [x] Schémas Pydantic v2 (UserPublic / UserPrivate / Token)
- [x] Configuration centralisée (pydantic-settings)
- [x] CRUD complet — Articles (GET, POST, PUT, PATCH, DELETE)
- [x] CRUD complet — Utilisateurs (GET, POST, PUT, DELETE)
- [x] Découpage en routers (routes/posts.py, routes/users.py)
- [x] Hashage des mots de passe (pwdlib + argon2)
- [x] Authentification JWT (PyJWT — login, token, /me)
- [x] Pages login et register (HTML + Jinja2)
- [x] Gestion de l'état d'authentification côté navigateur (JS)
- [x] Gestion globale des erreurs (HTML et API)
- [x] Tests automatisés (pytest-asyncio + httpx)
- [ ] Protection des routes (get_current_user sur POST/PUT/DELETE)
- [ ] Liaison user connecté → création de post (supprimer user_id hardcodé)
- [ ] Gestion des commentaires
- [ ] Upload d'images pour les articles
- [ ] Pagination et recherche
- [ ] Connexion avec le frontend React
- [ ] Déploiement

## Auteur

**Abdoul Aziz Baba**  
Développeur Fullstack — Douala, Cameroun