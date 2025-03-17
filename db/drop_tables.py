from ..app import database

"""Drop all tables defined in app.tables
"""

metadata = database.Base.metadata
metadata.drop_all(database.engine)