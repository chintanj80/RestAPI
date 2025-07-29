# Structuring FastAPI with Repository, Router & Business Logic Models: A Clean Architecture Guide

Enter the **Repository Pattern**, **Router Modules**, and the often overlooked but essential **Business Logic (Service Layer)**.`

These architectural patterns help you build scalable, testable, and maintainable APIs with clear separation of concerns.

# 🚀 What We’ll Cover

✅ What are Repository, Router, and Business Logic Models  
✅ How to structure your project using them  
✅ A working example with FastAPI + SQLAlchemy  
✅ Folder structure best practices  
✅ Benefits of using this pattern

# 🤔 Understanding the Key Layers

# 🗂 Repository Pattern

The **Repository Pattern** acts as a middleman between your business logic and the database. It 
abstracts direct DB calls and encapsulates all data-related operations.

**Why use it?**

- Easily swap databases (PostgreSQL, MongoDB, etc.)
- Makes unit testing easier (mock repositories)
- Keeps business logic independent of DB queries

# 🔀 Router Modules

FastAPI uses `APIRouter` to group endpoints. Router Modules are like route files in Express or Blueprints in Flask.

**Why use it?**

- Keeps routes modular
- Easy to scale as the app grows
- Organize APIs by domain (e.g., `users`, `products`, `orders`)

# ⚙️ Business Logic / Service Layer

This is the glue that connects everything. It contains your **actual application logic** — like validation, sending emails, password hashing, combining multiple operations, etc.

**Why use it?**

- Keeps routers clean and focused only on request/response
- Promotes reuse of complex logic
- Makes testing business workflows easier

# 📁 Recommended Folder Structure

```python
app/  
├── main.py  
├── api/  
│   └── v1/  
│       └── routes/  
│           └── user.py  
├── models/  
│   └── user.py  
├── schemas/  
│   └── user.py  
├── repositories/  
│   └── user.py  
├── services/  
│   └── user_service.py  
├── utils/  
│   └── email.py  
├── db/  
│   └── session.py
```

# ⚙ Setting It Up: A Quick Walkthrough

Let’s build a simple user management module.

# 1. 🧱 SQLAlchemy Model — `models/user.py`

```python
from sqlalchemy import Column, Integer, String  
from app.db.session import Base
class User(Base):  
 __tablename__ = "users"  
 id = Column(Integer, primary_key=True, index=True)  
 name = Column(String)  
 email = Column(String, unique=True, index=True)
```

  

# 2. 📦 Pydantic Schema — `schemas/user.py`

```python
from pydantic import BaseModel

class UserCreate(BaseModel):  
 name: str  
 email: str

class UserOut(BaseModel):  
 id: int  
 name: str  
 email: str  
 class Config:  
 orm_mode = True
```



# 3. 🗂 Repository — `repositories/user.py`

```python
from sqlalchemy.orm import Session  
from app.models.user import User  
from app.schemas.user import UserCreate

class UserRepository:  
 def __init__(self, db: Session):  
 self.db = db  
 def create_user(self, user: UserCreate):  
 db_user = User(**user.dict())  
 self.db.add(db_user)  
 self.db.commit()  
 self.db.refresh(db_user)  
 return db_user  
 def get_users(self):  
 return self.db.query(User).all()

```



# 4. 🧠 Business Logic (Service Layer) — `services/user_service.py`

```python
from sqlalchemy.orm import Session  
from app.repositories.user import UserRepository  
from app.schemas.user import UserCreate  
from app.utils.email import send_welcome_email

class UserService:  
 def __init__(self, db: Session):  
 self.repo = UserRepository(db)  
 def create_user_with_logic(self, user_data: UserCreate):  
 # Check if user already exists  
 existing = self.repo.get_users()  
 if any(u.email == user_data.email for u in existing):  
 raise ValueError("User with this email already exists")  
 # Create user  
 user = self.repo.create_user(user_data)  
 # Business logic: send welcome email  
 send_welcome_email(user.email)  
 return user
```



# 5. 🔗 Router — `api/v1/routes/user.py`

```python
from fastapi import APIRouter, Depends, HTTPException  
from sqlalchemy.orm import Session  
from app.db.session import get_db  
from app.schemas.user import UserCreate, UserOut  
from app.services.user_service import UserService


router = APIRouter()  
@router.post("/", response_model=UserOut)  
def create_user(user: UserCreate, db: Session = Depends(get_db)):  
 try:  
 service = UserService(db)  
 return service.create_user_with_logic(user)  
 except ValueError as e:  
 raise HTTPException(status_code=400, detail=str(e))  
@router.get("/", response_model=list[UserOut])  
def get_users(db: Session = Depends(get_db)):  
 return UserService(db).repo.get_users()
```



# 6. 🧬 DB Session — `db/session.py`

```python
from sqlalchemy import create_engine  
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})  
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  
Base = declarative_base()  
def get_db():  
 db = SessionLocal()  
 try:  
 yield db  
 finally:  
 db.close()
```

# ✅ Benefits of This Structure

- Clean separation of concerns
- Reusable and testable services and repositories
- Scalable API routing
- Improved code readability and maintenance
- Easier unit and integration testing

# 💡 Final Thoughts

This structure is more than just neat folder organization — it’s about **sustainable growth**.

As
 your app scales, separating business logic, database operations, and 
route handling will save you from massive refactoring pains.

Use:

- **Repositories** for database access
- **Services** for business logic
- **Routers** for endpoint definitions

It’s a game-changer for clean, modular API development with FastAPI.


