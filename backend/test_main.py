# test_main.py
import pytest
from fastapi.testclient import TestClient
from main import app

# On crée notre "robot" qui va parler à l'application
client = TestClient(app)


# ✅ TEST 1 : Est-ce que /api/posts répond bien ?
def test_get_all_posts():
    response = client.get("/api/posts")          # Le robot demande la liste des posts
    assert response.status_code == 200           # On vérifie que c'est OK (200)
    assert isinstance(response.json(), list)     # On vérifie que c'est bien une liste
    assert len(response.json()) > 0              # On vérifie qu'il y a au moins 1 post


# ✅ TEST 2 : Est-ce qu'on peut récupérer un post qui existe ?
def test_get_post_existant():
    response = client.get("/api/posts/1")        # Le robot demande le post n°1
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1                       # C'est bien le post n°1
    assert "title" in data                       # Il a bien un titre
    assert "content" in data                     # Il a bien un contenu


# ✅ TEST 3 : Que se passe-t-il si le post n'existe pas ?
def test_get_post_inexistant():
    response = client.get("/api/posts/9999")     # Le post 9999 n'existe pas
    assert response.status_code == 404           # On doit avoir une erreur 404
    assert response.json()["detail"] == "Post not found"


# ✅ TEST 4 : Et si on passe un ID qui n'est pas un nombre ?
def test_get_post_id_invalide():
    response = client.get("/api/posts/abc")      # "abc" c'est pas un nombre entier
    assert response.status_code == 422           # FastAPI doit rejeter ça (422)