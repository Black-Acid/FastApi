import sqlalchemy as sql
import sqlalchemy.ext.declarative as declarative
import sqlalchemy.orm as orm


DB_URL = "sqlite:///./sqlite3.db"

engine = sql.create_engine(DB_URL, connect_args={"check_same_thread": False})

sessionLocal = orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative.declarative_base()