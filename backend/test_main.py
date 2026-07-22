import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from main import app
from database import get_db, Base

# ─────────────────────────────────────────────
# CONFIGURATION DE LA BASE DE DONNÉES DE TEST
# ─────────────────────────────────────────────

# On crée une BD SQLite séparée juste pour les tests
# "memory" = elle n'existe que pendant le test, rien n'est sauvegardé sur le disque
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_blog.db"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def get_test_db():
    """Notre fausse BD de test, qui remplace la vraie pendant les tests."""
    async with TestSessionLocal() as session:
        yield session


# ─────────────────────────────────────────────
# FIXTURES (outils réutilisables pour les tests)
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def setup_database():
    """
    Cette fixture tourne avant ET après CHAQUE test.
    
    Avant : elle crée toutes les tables dans la BD de test (vide)
    Après  : elle efface tout pour que le test suivant reparte de zéro
    
    C'est comme préparer une table propre avant chaque repas,
    et tout débarrasser après.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # Créer les tables

    yield  # ← ici les tests s'exécutent

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)     # Effacer les tables


@pytest.fixture
async def client():
    """
    Notre robot de test qui envoie des requêtes à l'app.
    
    On lui dit d'utiliser la BD de test au lieu de la vraie BD,
    grâce au système d'override de FastAPI.
    """
    app.dependency_overrides[get_db] = get_test_db  # ← le "remplacement" de BD

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()  # On remet tout comme avant après le test


# ─────────────────────────────────────────────
# TESTS — UTILISATEURS
# ─────────────────────────────────────────────

async def test_creer_un_utilisateur(client):
    """On vérifie qu'on peut créer un utilisateur correctement."""
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com"
    })
    assert response.status_code == 201          # 201 = Créé avec succès
    data = response.json()
    assert data["username"] == "abdoul"
    assert data["email"] == "abdoul@example.com"
    assert "id" in data                         # L'utilisateur a bien un ID


async def test_creer_utilisateur_username_duplique(client):
    """On vérifie qu'on ne peut pas créer 2 utilisateurs avec le même pseudo."""
    # On crée le premier
    await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com"
    })
    # On essaie d'en créer un second avec le même username
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "autre@example.com"
    })
    assert response.status_code == 400          # 400 = Mauvaise requête
    assert "Username already exists" in response.json()["detail"]


async def test_recuperer_utilisateur_existant(client):
    """On vérifie qu'on peut récupérer un utilisateur par son ID."""
    # D'abord on le crée
    create = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com"
    })
    user_id = create.json()["id"]

    # Ensuite on le récupère
    response = await client.get(f"/api/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["username"] == "abdoul"


async def test_recuperer_utilisateur_inexistant(client):
    """On vérifie qu'on obtient bien une erreur 404 si l'utilisateur n'existe pas."""
    response = await client.get("/api/users/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_supprimer_utilisateur(client):
    """On vérifie qu'on peut supprimer un utilisateur."""
    create = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com"
    })
    user_id = create.json()["id"]

    # On supprime
    response = await client.delete(f"/api/users/{user_id}")
    assert response.status_code == 204          # 204 = Supprimé, pas de contenu

    # On vérifie qu'il n'existe plus
    response = await client.get(f"/api/users/{user_id}")
    assert response.status_code == 404


# ─────────────────────────────────────────────
# TESTS — ARTICLES (POSTS)
# ─────────────────────────────────────────────

@pytest.fixture
async def utilisateur(client):
    """
    Fixture qui crée un utilisateur prêt à l'emploi.
    Tous les tests de posts en ont besoin, donc on le met ici
    pour ne pas répéter ce code dans chaque test.
    """
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com"
    })
    return response.json()


async def test_creer_un_post(client, utilisateur):
    """On vérifie qu'on peut créer un article."""
    response = await client.post("/api/posts", json={
        "title": "Mon premier article",
        "content": "Contenu de test.",
        "user_id": utilisateur["id"]
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Mon premier article"
    assert data["content"] == "Contenu de test."


async def test_creer_post_utilisateur_inexistant(client):
    """On ne peut pas créer un post pour un utilisateur qui n'existe pas."""
    response = await client.post("/api/posts", json={
        "title": "Article fantôme",
        "content": "Contenu.",
        "user_id": 9999          # cet utilisateur n'existe pas
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_lister_tous_les_posts(client, utilisateur):
    """On vérifie que la liste des posts fonctionne."""
    # On crée 2 posts
    await client.post("/api/posts", json={
        "title": "Article 1", "content": "...", "user_id": utilisateur["id"]
    })
    await client.post("/api/posts", json={
        "title": "Article 2", "content": "...", "user_id": utilisateur["id"]
    })

    response = await client.get("/api/posts")
    assert response.status_code == 200
    assert len(response.json()) == 2            # Il doit y en avoir exactement 2


async def test_modifier_post_partiel(client, utilisateur):
    """On vérifie que le PATCH ne modifie que ce qu'on lui donne."""
    create = await client.post("/api/posts", json={
        "title": "Titre original",
        "content": "Contenu original.",
        "user_id": utilisateur["id"]
    })
    post_id = create.json()["id"]

    # On modifie seulement le titre
    response = await client.patch(f"/api/posts/{post_id}", json={
        "title": "Nouveau titre"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nouveau titre"
    assert data["content"] == "Contenu original."  # le contenu n'a pas changé !


async def test_supprimer_post(client, utilisateur):
    """On vérifie qu'on peut supprimer un post."""
    create = await client.post("/api/posts", json={
        "title": "À supprimer", "content": "...", "user_id": utilisateur["id"]
    })
    post_id = create.json()["id"]

    response = await client.delete(f"/api/posts/{post_id}")
    assert response.status_code == 204

    # Il ne doit plus exister
    response = await client.get(f"/api/posts/{post_id}")
    assert response.status_code == 404