from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request, status,BackgroundTasks
from requests import Session
from sqlalchemy import create_engine, Column, Integer, String, Boolean, PrimaryKeyConstraint, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, EmailStr, validator
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import time
from uuid import uuid4

# Database connection details (replace with your actual credentials)
DATABASE_URL = "sqlite:///contacts.db"

# Define database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a declarative base for SQLAlchemy models
Base = declarative_base()

# class APITimingMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
#         start_time = time.time()  # Capture the start time
#         response = await call_next(request)
#         process_time = time.time() - start_time  # Calculate processing time
        
#         # Log the time taken to process the request
#         print(f"Request: {request.url.path} took {process_time} seconds")
        
#         # Optionally, add the timing information to response headers
#         response.headers['X-Process-Time'] = str(process_time)
        
#         return response
    
# Define SQLAlchemy ORM models based on the provided schema
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    phonenumber = Column(Integer, nullable=False)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    email = Column(String, nullable=False)
    email_opt_in_status = Column(Boolean, nullable=False)
    sms_opt_in_status = Column(Boolean, nullable=False)
    matm_owner = Column(String, nullable=False)
    individual_id = Column(String, nullable=True)
    status = Column(String, nullable=True)
    contact_id = Column(String, nullable=True)
    
class ContactPointEmail(Base):
    __tablename__ = "email_opt_in"
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    matm_owner = Column(String, nullable=False)
    contact_id = Column(String, nullable=False) 

class ContactPointPhone(Base):
    __tablename__ = "mobile_opt_in"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(String, nullable=False)
    phonenumber = Column(Integer, nullable=False)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    matm_owner = Column(String, nullable=False)
    contact_id = Column(String, nullable=False) 

class Individual(Base):
    __tablename__ = "individaul"
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(Integer, nullable=False)
    individual_id = Column(Integer, nullable=False)

# Create all database tables if they don't exist
Base.metadata.create_all(engine)

# Create a dependency for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit= False)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


# PYDANTIC
class ContactBase(BaseModel):
    username: str
    email:EmailStr
    phonenumber: int
    email_opt_in_status: bool
    sms_opt_in_status: bool
    country: Optional[str]
    state: Optional[str]
    matm_owner: str
    
    @validator('username')
    def validate_username_length(cls, value):
        """Ensures username is not null and has a minimum length."""
        if not value:
            raise ValueError("username cannot be null")
        if len(value) < 3:
            raise ValueError("username must be at least 3 characters long")
        return value

    @validator('phonenumber')
    def validate_phonenumber_range(cls, value):
        """Validates phone number format (optional, adjust as needed)."""
        if not isinstance(value, int) or len(str(value)) != 10 or not (1 <= value <= 9999999999):
            raise ValueError("phonenumber must be a valid 10-digit integer")
        return value
    
async def write_email_opt_in(data: Contact, db:Session = Depends(get_db)):
    print("write_email_opt_in")
    try:
        email_opt_in = ContactPointEmail(
            username=data.username,
            email=data.email,
            country=data.country,
            state=data.state,
            matm_owner = data.matm_owner,
            contact_id = data.contact_id
        )
        db.add(email_opt_in)
        db.commit()
    except Exception as e:
        print(e)


async def write_mobile_opt_in(data: Contact, db:Session = Depends(get_db)):
    print("write_mobile_opt_in")
    try:
        mobile_opt_in = ContactPointPhone(
            username=data.username,
            phonenumber=data.phonenumber,
            country=data.country,
            state=data.state,
            matm_owner = data.matm_owner,
            contact_id = data.contact_id
        )
        db.add(mobile_opt_in)
        db.commit()
    except Exception as e:
        print(e)

async def update_contact(data:Individual, db,individual_id_new = str):
    new_individual = Individual(username= data.username, individual_id = individual_id_new)
    db.add(new_individual)
    db.commit()

@app.post("/contacts", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_contact(data: ContactBase,background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    start_time = time.time()
    contact_ins = Contact(username=data.username, phonenumber=data.phonenumber, country = data.country, state = data.state,
                        sms_opt_in_status= data.sms_opt_in_status, email = data.email, email_opt_in_status = data.email_opt_in_status,
                        matm_owner= data.matm_owner)
    message = "Contact added successfully"
    contact_ins.contact_id = uuid4().hex[:8]
    phone_result = db.execute(select(ContactPointPhone).filter(ContactPointPhone.phonenumber == data.phonenumber))
    phone = phone_result.scalars().all()
    email_result = db.execute(select(ContactPointEmail).filter(ContactPointEmail.email == data.email))
    email = email_result.scalars().all()

    # check for Matm Owner if Phone or email already in db
    matched_contacts = []
    matched_individuals = []
    try:
        for result_email in email:
            if result_email.matm_owner == data.matm_owner and result_email.username == data.username:
                matched_contacts.append(result_email.contact_id)
            elif result_email.matm_owner == data.matm_owner and result_email.username != data.username:
                raise ValueError("matching error on contact data")
            elif result_email.matm_owner != data.matm_owner and result_email.username == data.username:
                matched_individuals.append(result_email.contact_id)

        for result_phone in phone:
            if result_phone.matm_owner == data.matm_owner and result_phone.username == data.username:
                matched_contacts.append(result_phone.contact_id)
            elif result_phone.matm_owner == data.matm_owner and result_phone.username != data.username:
                raise ValueError("matching error on contact data")
            elif result_phone.matm_owner != data.matm_owner and result_phone.username == data.username:
                matched_individuals.append(result_phone.contact_id)

    except Exception as error:
        contact_ins.status = message = str(error)
    
    if matched_contacts:
        contact_ins = db.execute(select(Contact).filter(Contact.contact_id== matched_contacts[0]))
        contact_ins = contact_ins.scalars().one()
        contact_ins.state = data.state
        contact_ins.country = data.country
        contact_ins.status = f"updated - {start_time - time.time()}"
        message = "contact Updated"

    elif matched_individuals:
        individual_id = db.execute(select(Contact.individual_id).filter(Contact.contact_id == matched_individuals[0]))
        contact_ins.individual_id == individual_id
        contact_ins.status = f"created - {time.time()}"

    if message == "Contact added successfully" or matched_individuals:
            
        background_tasks.add_task(write_email_opt_in, contact_ins, db)
        background_tasks.add_task(write_mobile_opt_in, contact_ins, db)

    else:
        individual_id_new = uuid4().hex
        background_tasks.add_task(update_contact,contact_ins,db,individual_id_new),

    db.add(contact_ins)
    db.commit()

    duration = time.time() - start_time
    return ({'message': message, 'username': data.username, 'time taken':duration})


@app.get("/contacts") 
async def read_contacts(db: Session = Depends(get_db)):
    results = db.execute(select(Contact))
    users = results.scalars().all()
    return {"users": users}

@app.get("/email") 
async def read_contacts(db: Session = Depends(get_db)):
    results = db.execute(select(Contact))
    users = results.scalars().all()
    return {"email": users}

@app.get("/mobile") 
async def read_contacts(db: Session = Depends(get_db)):
    results = db.execute(select(Contact))
    users = results.scalars().all()
    return {"users": users}


@app.get("/contacts/{contact_id}", response_model=dict)
async def read_contact_by_id(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact