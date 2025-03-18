from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import pytest

from app.database import engine

# global application scope.  create Session class, engine
Session = sessionmaker()

@pytest.fixture(autouse=True)
def db_session():
    """From https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites"""
    ## Set Up Code
    # connect to the database
    connection = engine.connect()

    # begin a non-ORM transaction
    trans = connection.begin()

    # bind an individual Session to the connection, selecting
    # "create_savepoint" join_transaction_mode
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint"
    )

    yield session

    ## Tear Down Code
    session.close()

    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    trans.rollback()

    # return connection to the Engine
    connection.close()