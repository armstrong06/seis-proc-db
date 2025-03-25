from sqlalchemy import MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import MappedAsDataclass, DeclarativeBase, sessionmaker
from contextlib import contextmanager
from seis_proc_db.config import DB_URL


metadata_obj = MetaData(
    naming_convention={
        "uq": "uq_%(table_name)s_%(constraint_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


# Create a new Decorative Base
class Base(DeclarativeBase):
    metadata = metadata_obj


# create the database engine
engine = create_engine(DB_URL)

# create a factory for Session objects with a fixed configuration
Session = sessionmaker(engine)


@contextmanager
def get_db():
    """Provides a session to interact with the database. I got this from CHATGPT.

    Yields:
        _type_: _description_
    """
    db = Session()
    try:
        yield db
    finally:
        db.close()
