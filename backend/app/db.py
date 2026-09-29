from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./taskpilot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_order=True, primary_key=True, index=True)
    filename = Column(String, index=True)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    tasks = relationship("TaskRecord", back_populates="document", cascade="all, delete-orphan")

class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    title = Column(String)
    deadline = Column(String)
    priority = Column(String)
    action_required = Column(Text)
    status = Column(String, default="Pending")  # Pending, In Progress, Completed
    category = Column(String, default="Actionable")  # Actionable or Future
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("DocumentRecord", back_populates="tasks")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()