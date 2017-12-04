from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

"""This script creates an sqlite database with the schema defined below."""

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


class Models(Base):
    __tablename__ = 'models'
    # Here we define columns for the table address.
    # Notice that each column is also a normal Python instance attribute.
    id = Column(Integer, primary_key=True)
    model_id = Column(String(32), unique=True)
    filename = Column(String(250))
    created_date = Column(DateTime, nullable=False)
    original_file = Column(String(250))
    gltf_file = Column(String(250))
    bin_file = Column(String(250))
    glb_file = Column(String(250))
    zip_file = Column(String(250))

# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
db = create_engine('sqlite:///database.db')

# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
Base.metadata.create_all(db)