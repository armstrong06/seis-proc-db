from ..app import database

"""Create all tables defined in app.tables
"""
metadata = database.Base.metadata
metadata.create_all(database.engine)