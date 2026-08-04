"""
database.py
-----------
This file wires up SQLAlchemy: the engine (the actual connection to the
SQLite file on disk), the SessionLocal factory (creates a new DB "session"
per request), and the declarative Base that our models.py will inherit from.

Why SQLite? No server to install, it's just a file (taskflow.db) that gets
created automatically the first time you run the app. Good enough for this
project's scale (thousands of rows).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The database file will be created in the backend/ folder as taskflow.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./taskflow.db"

# check_same_thread=False is needed only for SQLite when used with FastAPI,
# because FastAPI can handle a request in a different thread than the one
# that created the connection.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our ORM models (User, Project, Task) will inherit from this Base.
Base = declarative_base()
