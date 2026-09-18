import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qa_platform.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_IN_RENDER")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    projects: Mapped[list["Project"]] = relationship(back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    website_url: Mapped[str] = mapped_column(String(1000))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user: Mapped["User"] = relationship(back_populates="projects")
    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")

class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(255))
    steps: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    project: Mapped["Project"] = relationship(back_populates="test_cases")

class TestRun(Base):
    __tablename__ = "test_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    project: Mapped["Project"] = relationship(back_populates="test_runs")
    results: Mapped[list["TestResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")

class TestResult(Base):
    __tablename__ = "test_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"))
    status: Mapped[str] = mapped_column(String(40))
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    run: Mapped["TestRun"] = relationship(back_populates="results")

Base.metadata.create_all(engine)

app = FastAPI(title="QA Testing Platform API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()

def token_for(user: User):
    payload = {"sub": str(user.id), "email": user.email, "admin": user.is_admin,
               "exp": datetime.now(timezone.utc) + timedelta(hours=24)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), session: Session = Depends(db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user

def admin_only(user: User = Depends(current_user)):
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user

class Login(BaseModel):
    email: EmailStr
    password: str

class Register(BaseModel):
    name: str
    email: EmailStr
    password: str

class ProjectIn(BaseModel):
    name: str
    website_url: str
    description: Optional[str] = None

class TestCaseIn(BaseModel):
    title: str
    steps: str
    expected_result: str

class TestRunIn(BaseModel):
    project_id: int

class ResultIn(BaseModel):
    run_id: int
    test_case_id: int
    status: str
    error_message: Optional[str] = None
    screenshot_url: Optional[str] = None
    duration_ms: Optional[int] = None

@app.on_event("startup")
def startup():
    with SessionLocal() as s:
        if not s.query(User).filter(User.email == ADMIN_EMAIL).first():
            s.add(User(name="Administrator", email=ADMIN_EMAIL, password_hash=pwd.hash(ADMIN_PASSWORD), is_admin=True))
            s.commit()

@app.get("/")
def root():
    return {"name": "QA Testing Platform API", "status": "online", "docs": "/docs", "admin": "/admin"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/admin")
def admin_page():
    return FileResponse("admin.html")

@app.post("/api/auth/register")
def register(data: Register, session: Session = Depends(db)):
    if session.query(User).filter(User.email == data.email).first():
        raise HTTPException(409, "Email already registered")
    u = User(name=data.name, email=data.email, password_hash=pwd.hash(data.password))
    session.add(u); session.commit(); session.refresh(u)
    return {"message": "registered", "id": u.id}

@app.post("/api/auth/login")
def login(data: Login, session: Session = Depends(db)):
    u = session.query(User).filter(User.email == data.email).first()
    if not u or not pwd.verify(data.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": token_for(u), "token_type": "bearer", "is_admin": u.is_admin}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}

@app.post("/api/projects")
def create_project(data: ProjectIn, user: User = Depends(current_user), session: Session = Depends(db)):
    p = Project(**data.model_dump(), user_id=user.id)
    session.add(p); session.commit(); session.refresh(p)
    return {"id": p.id, "name": p.name, "website_url": p.website_url}

@app.get("/api/projects")
def my_projects(user: User = Depends(current_user), session: Session = Depends(db)):
    rows = session.query(Project).filter(Project.user_id == user.id).order_by(Project.id.desc()).all()
    return [{"id": p.id, "name": p.name, "website_url": p.website_url, "description": p.description, "created_at": p.created_at} for p in rows]

@app.post("/api/projects/{project_id}/test-cases")
def create_test_case(project_id: int, data: TestCaseIn, user: User = Depends(current_user), session: Session = Depends(db)):
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id: raise HTTPException(404, "Project not found")
    t = TestCase(project_id=project_id, **data.model_dump())
    session.add(t); session.commit(); session.refresh(t)
    return {"id": t.id, **data.model_dump()}

@app.get("/api/projects/{project_id}/test-cases")
def get_test_cases(project_id: int, user: User = Depends(current_user), session: Session = Depends(db)):
    p = session.get(Project, project_id)
    if not p or p.user_id != user.id: raise HTTPException(404, "Project not found")
    return [{"id": t.id, "title": t.title, "steps": t.steps, "expected_result": t.expected_result} for t in p.test_cases]

@app.post("/api/test-runs")
def create_run(data: TestRunIn, user: User = Depends(current_user), session: Session = Depends(db)):
    p = session.get(Project, data.project_id)
    if not p or p.user_id != user.id: raise HTTPException(404, "Project not found")
    r = TestRun(project_id=p.id, status="queued")
    session.add(r); session.commit(); session.refresh(r)
    return {"id": r.id, "project_id": r.project_id, "status": r.status}

@app.post("/api/test-results")
def add_result(data: ResultIn, user: User = Depends(current_user), session: Session = Depends(db)):
    r = session.get(TestRun, data.run_id)
    if not r or r.project.user_id != user.id: raise HTTPException(404, "Test run not found")
    x = TestResult(**data.model_dump())
    session.add(x); r.status = "completed"; session.commit()
    return {"id": x.id, "status": x.status}

@app.get("/api/admin/dashboard")
def admin_dashboard(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return {
        "users": session.query(User).count(), "projects": session.query(Project).count(),
        "test_cases": session.query(TestCase).count(), "test_runs": session.query(TestRun).count(),
        "test_results": session.query(TestResult).count(),
        "passed": session.query(TestResult).filter(TestResult.status.ilike("passed")).count(),
        "failed": session.query(TestResult).filter(TestResult.status.ilike("failed")).count()
    }

@app.get("/api/admin/users")
def admin_users(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return [{"id":u.id,"name":u.name,"email":u.email,"is_admin":u.is_admin,"created_at":u.created_at}
            for u in session.query(User).order_by(User.id.desc()).all()]

@app.get("/api/admin/projects")
def admin_projects(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return [{"id":p.id,"name":p.name,"website_url":p.website_url,"user_id":p.user_id,
             "user_email":p.user.email,"created_at":p.created_at}
            for p in session.query(Project).order_by(Project.id.desc()).all()]

@app.get("/api/admin/test-cases")
def admin_test_cases(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return [{"id":t.id,"project_id":t.project_id,"project":t.project.name,"title":t.title,
             "steps":t.steps,"expected_result":t.expected_result}
            for t in session.query(TestCase).order_by(TestCase.id.desc()).all()]

@app.get("/api/admin/test-runs")
def admin_test_runs(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return [{"id":r.id,"project_id":r.project_id,"project":r.project.name,"status":r.status,
             "started_at":r.started_at,"finished_at":r.finished_at}
            for r in session.query(TestRun).order_by(TestRun.id.desc()).all()]

@app.get("/api/admin/test-results")
def admin_test_results(admin: User = Depends(admin_only), session: Session = Depends(db)):
    return [{"id":x.id,"run_id":x.run_id,"test_case_id":x.test_case_id,"status":x.status,
             "error_message":x.error_message,"screenshot_url":x.screenshot_url,"duration_ms":x.duration_ms}
            for x in session.query(TestResult).order_by(TestResult.id.desc()).all()]
