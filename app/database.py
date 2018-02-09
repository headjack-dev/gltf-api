from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
import os

"""This script creates an sqlite database with the schema defined below."""
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_FOLDER, 'database', 'database.db')

Base = declarative_base()


# Events are already handled by AWS API Gateway, or else should be handled by a logging microservice, not PER service
# class Events(Base):
#     __tablename__ = 'events'
#     # Here we define columns for the table person
#     # Notice that each column is also a normal Python instance attribute.
#     id = Column(Integer, primary_key=True)
#     event_id = Column(String(32))
#     name = Column(String(250), nullable=False)
#     created_date = Column(DateTime, nullable=False)
#     content = Column(Text)


class ModelsTable(Base):
    __tablename__ = 'models'
    # Here we define columns for the table address.
    # Notice that each column is also a normal Python instance attribute.
    model_id = Column(String(32), primary_key=True)
    filename = Column(String(250))
    created_date = Column(DateTime, nullable=False)
    source_file = Column(String(250))
    processed_file = Column(String(250))
    downloadable_file = Column(String(250))
    compressed = Column(Boolean)

    # Allows result of query to be converted to a dict, making it serializable
    # Usage: ModelTable.as_dict()
    # def as_dict(self):
        # return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
db = create_engine('sqlite:///' + DB_PATH)

# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
Base.metadata.create_all(db)