from fastapi import FastAPI, Request, Form
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from app.routers import books
from app.database import Base, engine, SessionLocal
import os
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
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
def add_book(title: str = Form(...), author: str = Form(...), description: str | None = Form(None), year: int | None = Form(None)):
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

@app.get("/books-list")
def books_list(request: Request):
    db = SessionLocal()
    try:
        books = db.query(models.Book).all()
    finally:
        db.close()

    return templates.TemplateResponse("books.html", {"request": request, "books": books})

@app.get("/edit-book/{book_id}")
def edit_book_form(book_id: int, request: Request):
    db = SessionLocal()
    try:
        book = db.query(models.Book).filter(models.Book.id == book_id).first()
    finally:
        db.close()

    if not book:
        return HTMLResponse(content="Book not found", status_code=404)

    return templates.TemplateResponse("edit_book.html", {"request": request, "book": book})

@app.post("/edit-book/{book_id}")
def edit_book(book_id: int, title: str = Form(...), author: str = Form(...), description: str | None = Form(None), year: int | None = Form(None)):
    db = SessionLocal()
    try:
        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if book:
            book.title = title
            book.author = author
            book.description = description
            book.year = year
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/books-list", status_code=303)

@app.post("/delete-book/{book_id}")
def delete_book(book_id: int):
    db = SessionLocal()
    try:
        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if book:
            db.delete(book)
            db.commit()
    finally:
        db.close()

    return RedirectResponse(url="/books-list", status_code=303)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
