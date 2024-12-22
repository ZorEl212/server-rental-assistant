from models.engine.db_engine import DBStorage
from resources.constants import API_ID, API_HASH

storage = DBStorage()
storage.reload()

