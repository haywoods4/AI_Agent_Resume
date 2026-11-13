from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Changed to db.sqlite3 
SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite3"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Replaced the PII (names/resumes) with anonymous tracking IDs to enforce the privacy boundary.
class EvaluationRecord(Base):
    __tablename__ = "audit_logs"

    evaluation_id = Column(String, primary_key=True, index=True)
    job_id = Column(String, index=True)
    verdict = Column(String)
    sanitized_payload = Column(String)
    policy_evaluations = Column(String)

Base.metadata.create_all(bind=engine)

# Added the specific database rollback safeguard .
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # Rollback on a failed write
        raise
    finally:
        db.close()     # Guaranteed session closure
