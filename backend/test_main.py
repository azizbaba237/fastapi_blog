import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from main import app
from database import get_db, Base
import io
from unittest.mock import patch, MagicMock


# =============================================================================
# TEST DATABASE SETUP
# =============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_blog.db"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def get_test_db():
    """Test database session — replaces the real one during tests."""
    async with TestSessionLocal() as session:
        yield session


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
async def setup_database():
    """
    Runs before and after EVERY test.
    Before : creates all tables in an empty test database.
    After  : drops everything so the next test starts clean.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """
    Async HTTP client wired to the FastAPI app.
    Swaps the real database for the test database via dependency override.
    """
    app.dependency_overrides[get_db] = get_test_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# --- User fixtures -----------------------------------------------------------

@pytest.fixture
async def utilisateur(client):
    """Creates a primary test user."""
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    return response.json()


@pytest.fixture
async def autre_utilisateur(client):
    """Creates a second user to test ownership/authorization rules."""
    response = await client.post("/api/users", json={
        "username": "autreuser",
        "email": "autre@example.com",
        "password": "password123",
    })
    return response.json()


@pytest.fixture
async def token(client, utilisateur):
    """Returns a valid JWT token for the primary user."""
    response = await client.post("/api/users/token", data={
        "username": "abdoul@example.com",
        "password": "password123",
    })
    return response.json()["access_token"]


@pytest.fixture
async def auth_headers(token):
    """Authorization headers for the primary user."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def autre_token(client, autre_utilisateur):
    """Returns a valid JWT token for the second user."""
    response = await client.post("/api/users/token", data={
        "username": "autre@example.com",
        "password": "password123",
    })
    return response.json()["access_token"]


@pytest.fixture
async def autre_auth_headers(autre_token):
    """Authorization headers for the second user."""
    return {"Authorization": f"Bearer {autre_token}"}


# --- Post fixture ------------------------------------------------------------

@pytest.fixture
async def post(client, utilisateur, auth_headers):
    """Creates a post owned by the primary user."""
    response = await client.post("/api/posts", json={
        "title": "Test Post",
        "content": "Test content.",
    }, headers=auth_headers)
    return response.json()


# =============================================================================
# USER TESTS — REGISTRATION
# =============================================================================

async def test_creer_un_utilisateur(client):
    """A new user can be registered with valid data."""
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "abdoul"
    assert data["email"] == "abdoul@example.com"
    assert "id" in data
    # Password must never appear in any response
    assert "password" not in data
    assert "password_hash" not in data


async def test_creer_utilisateur_mot_de_passe_trop_court(client):
    """Passwords shorter than 8 characters must be rejected (422)."""
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "abc",
    })
    assert response.status_code == 422


async def test_creer_utilisateur_username_duplique(client):
    """Two users cannot share the same username."""
    await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    response = await client.post("/api/users", json={
        "username": "abdoul",
        "email": "autre@example.com",
        "password": "password123",
    })
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]


async def test_creer_utilisateur_email_duplique(client):
    """Two users cannot share the same email."""
    await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    response = await client.post("/api/users", json={
        "username": "autreuser",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    assert response.status_code == 400
    assert "Email already exists" in response.json()["detail"]


async def test_creer_utilisateur_email_insensible_casse(client):
    """Email uniqueness check must be case-insensitive."""
    await client.post("/api/users", json={
        "username": "abdoul",
        "email": "abdoul@example.com",
        "password": "password123",
    })
    response = await client.post("/api/users", json={
        "username": "autreuser",
        "email": "ABDOUL@EXAMPLE.COM",
        "password": "password123",
    })
    assert response.status_code == 400


# =============================================================================
# USER TESTS — READ & DELETE
# =============================================================================

async def test_recuperer_utilisateur_profil_public(client, utilisateur):
    """GET /api/users/{id} returns only public fields — email must be hidden."""
    response = await client.get(f"/api/users/{utilisateur['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "abdoul"
    assert "email" not in data
    assert "password_hash" not in data


async def test_recuperer_utilisateur_inexistant(client):
    """Requesting a non-existent user must return 404."""
    response = await client.get("/api/users/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


async def test_supprimer_utilisateur_sans_auth(client, utilisateur):
    """Deleting a user without a token must return 401."""
    response = await client.delete(f"/api/users/{utilisateur['id']}")
    assert response.status_code == 401


async def test_supprimer_autre_utilisateur(client, utilisateur, autre_utilisateur, auth_headers):
    """A user cannot delete another user's account (403)."""
    response = await client.delete(
        f"/api/users/{autre_utilisateur['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 403


async def test_supprimer_son_propre_compte(client, utilisateur, auth_headers):
    """A user can delete their own account."""
    response = await client.delete(
        f"/api/users/{utilisateur['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    # User must no longer exist
    response = await client.get(f"/api/users/{utilisateur['id']}")
    assert response.status_code == 404


# =============================================================================
# USER TESTS — UPDATE
# =============================================================================

async def test_modifier_son_propre_compte(client, utilisateur, auth_headers):
    """A user can update their own username."""
    response = await client.patch(
        f"/api/users/{utilisateur['id']}",
        json={"username": "nouveaunom"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "nouveaunom"


async def test_modifier_autre_utilisateur(client, utilisateur, autre_utilisateur, auth_headers):
    """A user cannot update another user's account (403)."""
    response = await client.patch(
        f"/api/users/{autre_utilisateur['id']}",
        json={"username": "hacked"},
        headers=auth_headers,
    )
    assert response.status_code == 403


async def test_modifier_utilisateur_sans_auth(client, utilisateur):
    """Updating a user without a token must return 401."""
    response = await client.patch(
        f"/api/users/{utilisateur['id']}",
        json={"username": "nouveaunom"},
    )
    assert response.status_code == 401


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

async def test_login_valide(client, utilisateur):
    """A valid login must return a JWT token."""
    response = await client.post("/api/users/token", data={
        "username": "abdoul@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


async def test_login_mauvais_mot_de_passe(client, utilisateur):
    """A wrong password must return 401."""
    response = await client.post("/api/users/token", data={
        "username": "abdoul@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


async def test_login_email_inexistant(client):
    """Logging in with an unknown email must return 401."""
    response = await client.post("/api/users/token", data={
        "username": "nobody@example.com",
        "password": "password123",
    })
    assert response.status_code == 401


async def test_login_insensible_casse_email(client, utilisateur):
    """Login must work regardless of email case."""
    response = await client.post("/api/users/token", data={
        "username": "ABDOUL@EXAMPLE.COM",
        "password": "password123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_get_current_user(client, utilisateur, auth_headers):
    """GET /me must return the full private profile of the logged-in user."""
    response = await client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "abdoul"
    assert data["email"] == "abdoul@example.com"   # email visible only on /me
    assert "password_hash" not in data


async def test_get_current_user_sans_token(client):
    """GET /me without a token must return 401."""
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_get_current_user_token_invalide(client):
    """GET /me with a forged token must return 401."""
    response = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer fake.token.here"},
    )
    assert response.status_code == 401


# =============================================================================
# POST TESTS — CRUD
# =============================================================================

async def test_creer_un_post(client, utilisateur, auth_headers):
    """An authenticated user can create a post."""
    response = await client.post("/api/posts", json={
        "title": "Mon premier article",
        "content": "Contenu de test.",
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Mon premier article"
    assert data["content"] == "Contenu de test."
    assert data["author"]["username"] == "abdoul"
    # The post must belong to the logged-in user
    assert data["user_id"] == utilisateur["id"]


async def test_creer_post_sans_auth(client):
    """Creating a post without a token must return 401."""
    response = await client.post("/api/posts", json={
        "title": "Article",
        "content": "Contenu.",
    })
    assert response.status_code == 401


async def test_lister_tous_les_posts(client, utilisateur, auth_headers):
    """The post list is public and returns all posts."""
    await client.post("/api/posts", json={
        "title": "Article 1", "content": "...",
    }, headers=auth_headers)
    await client.post("/api/posts", json={
        "title": "Article 2", "content": "...",
    }, headers=auth_headers)

    # No auth required to list posts
    response = await client.get("/api/posts")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_recuperer_post_existant(client, post):
    """An existing post can be retrieved by ID without auth."""
    response = await client.get(f"/api/posts/{post['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Post"


async def test_recuperer_post_inexistant(client):
    """Requesting a non-existent post must return 404."""
    response = await client.get("/api/posts/9999")
    assert response.status_code == 404


# =============================================================================
# POST TESTS — AUTHORIZATION (ownership)
# =============================================================================

async def test_modifier_son_propre_post(client, post, auth_headers):
    """The post owner can partially update their post (PATCH)."""
    response = await client.patch(
        f"/api/posts/{post['id']}",
        json={"title": "Nouveau titre"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nouveau titre"
    assert data["content"] == "Test content."   # unchanged field


async def test_modifier_post_sans_auth(client, post):
    """Updating a post without a token must return 401."""
    response = await client.patch(
        f"/api/posts/{post['id']}",
        json={"title": "Nouveau titre"},
    )
    assert response.status_code == 401


async def test_modifier_post_autre_utilisateur(client, post, autre_auth_headers):
    """A user cannot update a post they don't own (403)."""
    response = await client.patch(
        f"/api/posts/{post['id']}",
        json={"title": "Titre volé"},
        headers=autre_auth_headers,
    )
    assert response.status_code == 403


async def test_remplacer_son_propre_post(client, post, auth_headers):
    """The post owner can fully replace their post (PUT)."""
    response = await client.put(
        f"/api/posts/{post['id']}",
        json={"title": "Titre remplacé", "content": "Contenu remplacé."},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Titre remplacé"
    assert data["content"] == "Contenu remplacé."


async def test_remplacer_post_autre_utilisateur(client, post, autre_auth_headers):
    """A user cannot fully replace a post they don't own (403)."""
    response = await client.put(
        f"/api/posts/{post['id']}",
        json={"title": "Volé", "content": "Volé."},
        headers=autre_auth_headers,
    )
    assert response.status_code == 403


async def test_supprimer_son_propre_post(client, post, auth_headers):
    """The post owner can delete their post."""
    response = await client.delete(
        f"/api/posts/{post['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    response = await client.get(f"/api/posts/{post['id']}")
    assert response.status_code == 404


async def test_supprimer_post_sans_auth(client, post):
    """Deleting a post without a token must return 401."""
    response = await client.delete(f"/api/posts/{post['id']}")
    assert response.status_code == 401


async def test_supprimer_post_autre_utilisateur(client, post, autre_auth_headers):
    """A user cannot delete a post they don't own (403)."""
    response = await client.delete(
        f"/api/posts/{post['id']}",
        headers=autre_auth_headers,
    )
    assert response.status_code == 403


# =============================================================================
# HTML PAGE TESTS
# =============================================================================

async def test_home_page_loads(client):
    """Home page must return 200 with HTML content."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_home_page_shows_posts(client, utilisateur, auth_headers):
    """Home page must display posts once they exist."""
    await client.post("/api/posts", json={
        "title": "Article visible", "content": "Contenu.",
    }, headers=auth_headers)
    response = await client.get("/")
    assert response.status_code == 200
    assert "Article visible" in response.text


async def test_post_page_loads(client, post):
    """Post detail page must return 200 for an existing post."""
    response = await client.get(f"/posts/{post['id']}")
    assert response.status_code == 200
    assert "Test Post" in response.text


async def test_post_page_404(client):
    """Post detail page must return 404 for a non-existent post."""
    response = await client.get("/posts/9999")
    assert response.status_code == 404


async def test_user_posts_page_loads(client, utilisateur, post):
    """User posts page must return 200 and show the user's posts."""
    response = await client.get(f"/users/{utilisateur['id']}/posts")
    assert response.status_code == 200
    assert "Test Post" in response.text


async def test_user_posts_page_404(client):
    """User posts page must return 404 for a non-existent user."""
    response = await client.get("/users/9999/posts")
    assert response.status_code == 404


async def test_login_page_loads(client):
    """Login page must return 200 with HTML content."""
    response = await client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_register_page_loads(client):
    """Register page must return 200 with HTML content."""
    response = await client.get("/register")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_account_page_loads(client):
    """Account page must return 200 with HTML content."""
    response = await client.get("/account")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    
# =============================================================================
# PROFILE PICTURE TESTS
# =============================================================================

# This is a minimal valid 1x1 JPEG image in bytes
# Used to simulate a real image file without needing an actual file on disk
FAKE_JPEG = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
    b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
    b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e'
    b'\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b'
    b'\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b\x1b'
    b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00'
    b'\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00'
    b'\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00'
    b'\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81'
    b'\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19'
    b'\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86'
    b'\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4'
    b'\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2'
    b'\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9'
    b'\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5'
    b'\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb'
    b'\xd4P\x00\x00\x00\x1f\xff\xd9'
)


async def test_upload_photo_de_profil(client, utilisateur, auth_headers):
    """
    Uploading a profile picture must call Cloudinary and store the returned URL.
    
    We mock cloudinary.uploader.upload to avoid real network calls.
    The mock returns a fake URL as Cloudinary would.
    """
    fake_cloudinary_url = "https://res.cloudinary.com/test/image/upload/v123/fastapi_blog/profile_pics/abc.jpg"

    # patch() temporarily replaces the real Cloudinary upload with our fake one
    with patch("image_utils.cloudinary.uploader.upload") as mock_upload:
        mock_upload.return_value = {"secure_url": fake_cloudinary_url}

        response = await client.patch(
            f"/api/users/{utilisateur['id']}/picture",
            headers=auth_headers,
            files={"file": ("photo.jpg", io.BytesIO(FAKE_JPEG), "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    # The image_path must now be the Cloudinary URL, not a local path
    assert data["image_path"] == fake_cloudinary_url
    # Cloudinary upload must have been called exactly once
    mock_upload.assert_called_once()


async def test_upload_photo_sans_auth(client, utilisateur):
    """Uploading a picture without a token must return 401."""
    response = await client.patch(
        f"/api/users/{utilisateur['id']}/picture",
        files={"file": ("photo.jpg", io.BytesIO(FAKE_JPEG), "image/jpeg")},
    )
    assert response.status_code == 401


async def test_upload_photo_autre_utilisateur(client, utilisateur, autre_auth_headers):
    """A user cannot upload a picture on another user's account (403)."""
    response = await client.patch(
        f"/api/users/{utilisateur['id']}/picture",
        headers=autre_auth_headers,
        files={"file": ("photo.jpg", io.BytesIO(FAKE_JPEG), "image/jpeg")},
    )
    assert response.status_code == 403


async def test_upload_fichier_invalide(client, utilisateur, auth_headers):
    """Uploading a non-image file must return 400."""
    fake_pdf = b"%PDF-1.4 fake content"

    with patch("image_utils.cloudinary.uploader.upload"):
        response = await client.patch(
            f"/api/users/{utilisateur['id']}/picture",
            headers=auth_headers,
            files={"file": ("doc.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        )

    assert response.status_code == 400


async def test_supprimer_photo_de_profil(client, utilisateur, auth_headers):
    """
    After uploading a picture, the user can delete it.
    The image_path must fall back to the default picture.
    """
    fake_url = "https://res.cloudinary.com/test/image/upload/v123/fastapi_blog/profile_pics/abc.jpg"

    # First upload a picture
    with patch("image_utils.cloudinary.uploader.upload") as mock_upload:
        mock_upload.return_value = {"secure_url": fake_url}
        await client.patch(
            f"/api/users/{utilisateur['id']}/picture",
            headers=auth_headers,
            files={"file": ("photo.jpg", io.BytesIO(FAKE_JPEG), "image/jpeg")},
        )

    # Then delete it
    with patch("image_utils.cloudinary.uploader.destroy") as mock_destroy:
        response = await client.delete(
            f"/api/users/{utilisateur['id']}/picture",
            headers=auth_headers,
        )
        mock_destroy.assert_called_once()

    assert response.status_code == 200
    # image_path must fall back to the default
    assert response.json()["image_path"] == "/static/profile_pics/default.jpg"


async def test_supprimer_photo_inexistante(client, utilisateur, auth_headers):
    """Deleting a picture when none is set must return 400."""
    response = await client.delete(
        f"/api/users/{utilisateur['id']}/picture",
        headers=auth_headers,
    )
    assert response.status_code == 400


