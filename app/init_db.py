from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from app.security import hash_password


def init_db():
    models.Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    admin = db.query(models.User).filter_by(username="admin").first()

    if not admin:
        admin = models.User(
            username="admin",
            password_hash=hash_password("admin123"),
            is_admin=True
        )
        db.add(admin)
        db.commit()
        print("Admin account created (admin / admin123)")
    else:
        print("Admin already exists")

    if db.query(models.Book).count() == 0:
        books = [
            models.Book(
                title="The Pragmatic Programmer",
                author="Andrew Hunt, David Thomas",
                year=1999,
                description="A classic book about software craftsmanship."
            ),
            models.Book(
                title="Clean Code",
                author="Robert C. Martin",
                year=2008,
                description="A handbook of agile software craftsmanship."
            ),
            models.Book(
                title="Design Patterns",
                author="Gamma, Helm, Johnson, Vlissides",
                year=1994,
                description="Elements of Reusable Object-Oriented Software."
            ),
        ]

        db.add_all(books)
        db.commit()
        print("Sample books inserted.")
    else:
        print("Books already exist — skipping initialization.")

    db.close()


if __name__ == "__main__":
    init_db()
