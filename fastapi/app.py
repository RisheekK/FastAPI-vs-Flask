from http.client import HTTPException
from fastapi import BackgroundTasks, FastAPI, Request, Depends, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.responses import Response
from asyncio import create_task
import string
from typing import Optional
from uuid import uuid4

# SQLALCHEMY 
engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3", connect_args={"check_same_thread": False})


SessionLocal = async_sessionmaker(engine, expire_on_commit= False)

class APITimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()  # Capture the start time
        response = await call_next(request)
        process_time = time.time() - start_time  # Calculate processing time
        
        # Log the time taken to process the request
        print(f"Request: {request.url.path} took {process_time} seconds")
        
        # Optionally, add the timing information to response headers
        response.headers['X-Process-Time'] = str(process_time)
        
        return response

class Base(DeclarativeBase):
    pass

class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True,nullable=False)
    username: Mapped[str] = mapped_column( nullable=False)
    phonenumber: Mapped[int] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(nullable=False)
    email_opt_in_status: Mapped[bool] = mapped_column(nullable=False)
    sms_opt_in_status: Mapped[bool] = mapped_column(nullable=False)
    matm_owner: Mapped[str] = mapped_column(nullable=False)
    individual_id: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)
    contact_id: Mapped[str] = mapped_column(nullable=True)
    
class ContactPointEmail(Base):
    __tablename__ = "email_opt_in"
    id: Mapped[int] = mapped_column(primary_key=True,nullable=False,autoincrement=True)
    username: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(nullable=True)
    matm_owner: Mapped[str] = mapped_column(nullable=False)
    contact_id: Mapped[str] = mapped_column(nullable=False) 

class ContactPointPhone(Base):
    __tablename__ = "mobile_opt_in"
    id: Mapped[int] = mapped_column(primary_key=True,nullable=False,autoincrement=True)
    username: Mapped[str] = mapped_column(nullable=False)
    phonenumber: Mapped[int] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(nullable=True)
    matm_owner: Mapped[str] = mapped_column(nullable=False)
    contact_id: Mapped[str] = mapped_column(nullable=False)

class Individual(Base):
    __tablename__ = "individaul"
    id: Mapped[int] = mapped_column(primary_key=True,nullable=False,autoincrement=True)
    username: Mapped[str] = mapped_column(nullable=False)
    individual_id: Mapped[int] = mapped_column(nullable=False)
    


async def get_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

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


# FASTAPI
app = FastAPI()

app.add_middleware(APITimingMiddleware)

async def write_email_opt_in(data: Contact, db: AsyncSession):
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
        await db.commit()
    except Exception as e:
        print(e)


async def write_mobile_opt_in(data: Contact, db:AsyncSession):
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
        await db.commit()
    except Exception as e:
        print(e)

async def update_contact(data:Individual, db:AsyncSession):
    individual_id_new = uuid4().hex
    new_individual = Individual(username= data.username, individual_id = individual_id_new)
    db.add(new_individual)
    await db.commit()


@app.post("/contacts")
async def index(data: ContactBase, db: AsyncSession = Depends(get_db)):
    start_time = time.time()
    contact_ins = Contact(username=data.username, phonenumber=data.phonenumber, country = data.country, state = data.state,
                        sms_opt_in_status= data.sms_opt_in_status, email = data.email, email_opt_in_status = data.email_opt_in_status,
                        matm_owner= data.matm_owner)
    message = "Contact added successfully"
    contact_ins.contact_id = uuid4().hex[:8]
    phone_result = await db.execute(select(ContactPointPhone).filter(ContactPointPhone.phonenumber == data.phonenumber))
    phone = phone_result.scalars().all()
    email_result = await db.execute(select(ContactPointEmail).filter(ContactPointEmail.email == data.email))
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
        contact_ins = await db.execute(select(Contact).filter(Contact.contact_id== matched_contacts[0]))
        contact_ins = contact_ins.scalars().one()
        contact_ins.state = data.state
        contact_ins.country = data.country
        contact_ins.status = f"updated - {start_time - time.time()}"
        message = "contact Updated"

    elif matched_individuals:
        individual_id = await db.execute(select(Contact.individual_id).filter(Contact.contact_id == matched_individuals[0]))
        contact_ins.individual_id == individual_id
        contact_ins.status = f"created - {time.time()}"

    if message == "Contact added successfully" or matched_individuals:
            
        write_email_task = create_task(write_email_opt_in(contact_ins,db))
        write_mobile_task = create_task(write_mobile_opt_in(contact_ins,db))

    else:
        write_individual_task = create_task(update_contact(contact_ins,db))

    db.add(contact_ins)
    await db.commit()

    await write_email_task

    duration = time.time() - start_time
    return ({'message': message, 'username': data.username, 'time taken':duration})

@app.get("/contacts")
async def get_users(db: AsyncSession = Depends(get_db)):
    results = await db.execute(select(Contact))
    users = results.scalars().all()
    return {"contacts": users}

@app.get("/email")
async def get_email(db: AsyncSession = Depends(get_db)):
    results = await db.execute(select(ContactPointEmail))
    emails = results.scalars().all()
    return {"email": emails}

@app.get("/mobile")
async def get_mobile(db: AsyncSession = Depends(get_db)):
    results = await db.execute(select(ContactPointPhone))
    mobile_numbers = results.scalars().all()
    return {"Phone numbers": mobile_numbers}

@app.get("/contacts/{item_id}")
async def get_contact(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == item_id))
    contact =result.scalars().first()
    if contact == None:
            raise HTTPException(status_code=404, detail="contact not found")
    return {"user": contact}

@app.get("/individual")
async def get_individual(db: AsyncSession = Depends(get_db)):
    results = await db.execute(select(Individual))
    individual= results.scalars().all()
    return {"individuals": individual}