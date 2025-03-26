import sqlalchemy as sql
import sqlalchemy.ext.declarative as declarative
import sqlalchemy.orm as orm


DB_URL = "sqlite:///./sqlite3.db"

engine = sql.create_engine(
    DB_URL, 
    connect_args={"check_same_thread": False},
    pool_size=10,        # ✅ Increase the number of concurrent connections
    max_overflow=20,     # ✅ Allow temporary extra connections
    pool_timeout=30,     # ✅ Wait time before failing
    pool_recycle=1800
)

sessionLocal = orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative.declarative_base()