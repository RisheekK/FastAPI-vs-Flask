from uuid import uuid4
from flask import Flask, jsonify, request
from requests import Session
from sqlalchemy import create_engine, Column, Integer, String, Boolean, PrimaryKeyConstraint, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import time
import json
from marshmallow import Schema, fields, validates, validates_schema
import marshmallow

app = Flask(__name__)

app.app_context().push()

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    print(f"Request took {duration} seconds")
    response.headers['X-Response-Time'] = str(duration)
    return response

# Database connection details (replace with your actual credentials)
DATABASE_URL = "sqlite:///contacts.db"

# Define database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a declarative base for SQLAlchemy models
Base = declarative_base()

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    

app = Flask(__name__)
app.app_context().push()

class ContactSchema(marshmallow.Schema):
    username = fields.Str(required=True, validate=lambda value: len(value) >= 3)
    email = fields.Email()
    phonenumber = fields.Integer(validate=lambda value: 1 <= value <= 9999999999)
    email_opt_in_status = fields.Boolean()
    sms_opt_in_status = fields.Boolean()
    country = fields.Str(allow_none=True)
    state = fields.Str(allow_none=True)
    matm_owner = fields.Str(allow_none= False)


    @validates('username')
    def validate_username_length(self, value):
        if not value:
            raise marshmallow.ValidationError("username cannot be null")

    @validates_schema
    def validate_phonenumber_type(self, data):
        if not isinstance(data['phonenumber'], int):
            raise marshmallow.ValidationError("phonenumber must be an integer")

user_schema = ContactSchema()
users_schema = ContactSchema(many=True)

@app.route('/contacts', methods=['GET'])
def get_users(db: Session = (get_db)):
    results = db.execute(select(Contact))
    users = results.scalars().all()
    return {"users": users}

@app.route('/contacts', methods=['POST'])
def add_user(db: Session = (get_db)):
    start_time = time.time()
    data = user_schema.load(request.json)
    errors = user_schema.validate(**data)
    if errors:
        return jsonify(errors), 400


    new_contact = Contact(**data)
    db.session.add(new_contact)
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

    username = data["username"]

    return jsonify({'message': 'User added successfully', 'username': username}), 201

@app.route('/email', methods=['GET'])
def get_email():
    emails = ContactPointEmail.query.all()
    return jsonify(users_schema.dump(emails))

@app.route('/mobile', methods=['GET'])
def get_mobile():
    mobile = ContactPointPhone.query.all()
    return jsonify(users_schema.dump(mobile))

if __name__ == '__main__':
    app.run(debug=True)