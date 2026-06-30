# FastAPI Blog

Application de blog full-stack avec une API backend en **FastAPI** et une interface utilisateur en **React (Vite)**.

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
- [Documentation de l'API](#documentation-de-lapi)
- [Roadmap](#roadmap)
- [Auteur](#auteur)

## Aperçu

Ce projet est un blog permettant aux utilisateurs de créer, consulter, modifier et supprimer des articles. Il est composé de deux parties indépendantes :

- **backend/** : une API REST développée avec FastAPI
- **frontend/** : une interface web développée avec React

## Stack technique

**Backend**
- Python 3.x
- FastAPI
- [uv](https://docs.astral.sh/uv/) (gestion des dépendances et de l'environnement virtuel)
- Pydantic (validation des données)

**Frontend**
- React (Vite)
- JavaScript / JSX
- Axios (requêtes HTTP)

> Le projet est encore en début de développement. La base de données et l'authentification ne sont pas encore en place ; cette section sera complétée au fur et à mesure de l'avancement.

## Structure du projet

```
fastapi_blog/
├── backend/
│   ├── main.py
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example
├── .gitignore
└── README.md
```

> Adapte cette arborescence si la structure réelle de ton projet diffère.

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
`uv sync` installe automatiquement les dépendances listées dans `pyproject.toml` et crée l'environnement virtuel.

### Frontend

```bash
cd frontend
npm install
```

## Variables d'environnement

Crée un fichier `.env` dans le dossier `frontend/` :

```
VITE_API_URL=http://localhost:8000
```

(Le backend n'a pas encore de variables d'environnement nécessaires à ce stade du projet.)

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

## Documentation de l'API

FastAPI génère automatiquement une documentation interactive :

- Swagger UI : `http://localhost:8000/docs`
- Redoc : `http://localhost:8000/redoc`

## Roadmap

- [ ] Mise en place de la base de données
- [ ] Création des modèles d'articles (CRUD)
- [ ] Authentification complète (inscription / connexion)
- [ ] Gestion des commentaires
- [ ] Upload d'images pour les articles
- [ ] Pagination et recherche d'articles
- [ ] Déploiement (backend + frontend)

## Auteur

**Abdoul Aziz Baba**
Développeur Fullstack — Douala, Cameroun
