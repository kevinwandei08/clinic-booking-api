from app.database import Base, engine
from app import models  # Registers all model classes with Base.metadata


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created or already exist.")


if __name__ == "__main__":
    create_tables()