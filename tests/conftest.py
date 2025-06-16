from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import pytest
from unittest import mock
import shutil
import os
from seis_proc_db.database import engine

# global application scope.  create Session class, engine
Session = sessionmaker()


@pytest.fixture
def mock_pytables_config():
    d = "./tests/pytables_outputs"
    if os.path.exists(d):
        try:
            shutil.rmtree(d)
        except Exception as e:
            print(f"Ran into error {e} when trying to remove test pytables outdir")
    with mock.patch(
        "seis_proc_db.pytables_backend.HDF_BASE_PATH",
        "./tests/pytables_outputs",
    ):
        yield


@pytest.fixture
def db_session():
    """From https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites"""
    ## Set Up Code
    # connect to the database
    connection = engine.connect()

    # begin a non-ORM transaction
    trans = connection.begin()

    # bind an individual Session to the connection, selecting
    # "create_savepoint" join_transaction_mode
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    ## Tear Down Code
    session.close()

    # rollback - everything that happened with the
    # Session above (including calls to commit())
    # is rolled back.
    trans.rollback()

    # return connection to the Engine
    connection.close()
