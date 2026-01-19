from fastapi import FastAPI, Request, Form, Depends, HTTPException
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from starlette import status
from app import models
from app.database import Base, engine, SessionLocal
from app.init_db import init_db
from app.models import User, Book, Loan
from app.routers import books
from app.security import hash_password, verify_password
from datetime import datetime

app = FastAPI(title="LibraryLite")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(books.router)


@app.on_event("startup")
def startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    username = request.cookies.get("user")

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get("user")
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()

def admin_required(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


@app.get("/")
def home(request: Request, user: User | None = Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user
        }
    )

@app.get("/books-list")
def books_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional)
):
    books = db.query(Book).all()

    borrowed_book_ids = {
        loan.book_id
        for loan in db.query(Loan)
        .filter(Loan.returned_at == None)
        .all()
    }

    return templates.TemplateResponse(
        "books.html",
        {
            "request": request,
            "books": books,
            "borrowed_book_ids": borrowed_book_ids,
            "user": user
        }
    )

@app.post("/borrow/{book_id}")
def borrow_book(
    book_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    active_loan = db.query(Loan).filter(
        Loan.book_id == book_id,
        Loan.returned_at == None
    ).first()

    if active_loan:
        raise HTTPException(400, "Book already borrowed")

    loan = Loan(user_id=user.id, book_id=book_id)
    db.add(loan)
    db.commit()

    return RedirectResponse("/books-list", status_code=303)


@app.get("/my-loans")
def my_loans(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loans = (
        db.query(Loan)
        .join(Book)
        .filter(
            Loan.user_id == user.id,
            Loan.returned_at == None
        )
        .all()
    )

    return templates.TemplateResponse(
        "my_loans.html",
        {
            "request": request,
            "loans": loans
        }
    )

@app.post("/return/{loan_id}")
def return_book(
    loan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    loan = db.query(Loan).filter(
        Loan.id == loan_id,
        Loan.user_id == user.id,
        Loan.returned_at == None
    ).first()

    if not loan:
        raise HTTPException(404, "Loan not found")

    loan.returned_at = datetime.utcnow()
    db.commit()

    return RedirectResponse("/my-loans", status_code=303)

@app.get("/add-book")
def add_book_form(
    request: Request,
    admin: User = Depends(admin_required)
):
    return templates.TemplateResponse("add_book.html", {"request": request})

@app.post("/add-book")
def add_book(
    title: str = Form(...),
    author: str = Form(...),
    description: str = Form(None),
    year: int = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    book = models.Book(
        title=title,
        author=author,
        description=description,
        year=year
    )

    db.add(book)
    db.commit()

    return RedirectResponse("/books-list", status_code=303)

@app.get("/edit-book/{book_id}")
def edit_book_form(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return templates.TemplateResponse(
        "edit_book.html",
        {
            "request": request,
            "book": book
        }
    )

@app.post("/edit-book/{book_id}")
def edit_book(
    book_id: int,
    title: str = Form(...),
    author: str = Form(...),
    description: str | None = Form(None),
    year: int | None = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.title = title
    book.author = author
    book.description = description
    book.year = year

    db.commit()

    return RedirectResponse("/books-list", status_code=303)


@app.post("/delete-book/{book_id}")
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    book = db.query(models.Book).filter(models.Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()

    return RedirectResponse("/books-list", status_code=303)

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "User already exists")

    user = User(
        username=username,
        password_hash=hash_password(password)
    )
    db.add(user)
    db.commit()

    response = RedirectResponse("/", status_code=303)
    response.set_cookie("user", username, httponly=True)
    return response

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie("user", username, httponly=True)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("user")
    return response
