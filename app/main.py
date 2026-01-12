from fastapi import FastAPI, Request
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.routers import books
from app.database import Base, engine
import os
from fastapi import Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LibraryLite")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(books.router)


@app.on_event("startup")
async def startup_event():
    from app.init_db import init_db
    init_db()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add-book")
def add_book(
    title: str = Form(...),
    author: str = Form(...),
    description: str | None = Form(None),
    year: int | None = Form(None)
):
    db: Session = SessionLocal()
    try:
        book = models.Book(
            title=title,
            author=author,
            description=description,
            year=year
        )
        db.add(book)
        db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/", status_code=303)

@app.get("/add-book")
def add_book_form(request: Request):
    return templates.TemplateResponse("add_book.html", {"request": request})

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
