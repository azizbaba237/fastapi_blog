from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is awesome",
        "content": "his framework is really easy to use and super fast.",
        "date_posted": "June 29, 2026",
    },

    {
        "id": 2,
        "author": "John doe",
        "title": "Python is Great for web Developper",
        "content": "Python is Great for web Developper, and FastAPI makes it even better.",
        "date_posted": "June 29, 2026",
    },
]

@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home Page"})  
