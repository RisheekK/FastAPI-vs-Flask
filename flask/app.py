import time
from uuid import uuid4
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from marshmallow import Schema, fields

# Flask app initialization
app = Flask(__name__)

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request.start_time
    print(f"Request took {duration} seconds")
    response.headers['X-Response-Time'] = str(duration)
    return response

# Configure connection string to your database
engine = create_engine('sqlite:///contacts.db')

# Create a declarative base for ORM classes
Base = declarative_base()

# Define Marshmallow schemas for data validation
class ContactSchema(Schema):
    username = fields.Str(required=True)
    phonenumber = fields.Int(required=True)
    country = fields.Str()
    state = fields.Str()
    email = fields.Email(required=True)
    email_opt_in_status = fields.Bool(required=True)
    sms_opt_in_status = fields.Bool(required=True)
    matm_owner = fields.Str(required=True)
    individual_id = fields.Str()
    status = fields.Str()
    contact_id = fields.Str()

class ContactPointEmailSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    country = fields.Str()
    state = fields.Str()
    matm_owner = fields.Str(required=True)
    contact_id = fields.Str(required=True)

class ContactPointPhoneSchema(Schema):
    username = fields.Str(required=True)
    phonenumber = fields.Int(required=True)
    country = fields.Str()
    state = fields.Str()
    matm_owner = fields.Str(required=True)
    contact_id = fields.Str(required=True)

class IndividualSchema(Schema):
    username = fields.Str(required=True)  # Consider changing type to String
    individual_id = fields.Int(required=True)


# Define ORM classes based on provided schema
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
    __tablename__ = "individaul"  # Typo corrected to "individual"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    username = Column(Integer, nullable=False)  # Consider changing type to String
    individual_id = Column(Integer, nullable=False)

# Create database tables (Comment out after initial creation)
Base.metadata.create_all(engine)

# Create a session object
Session = sessionmaker(bind=engine)
session = Session()

contact_schema = ContactSchema(many=True)
email_schema = ContactPointEmailSchema(many=True)
mobile_schema = ContactPointPhoneSchema(many = True)
individual_schema = ContactPointEmailSchema(many = True)

@app.route('/contacts', methods=['GET'])
def get_contacts():
    # Get all contacts
    contacts = session.query(Contact).all()
    return jsonify(contact_schema.dump(contacts))

@app.route('/contacts', methods=['POST'])    
def post_contact():
    start_time = time.time()
    content = request.get_json()
    schema = ContactSchema()
    # Validate data
    errors = schema.validate(content)
    if errors:
        return jsonify(errors), 400  # Bad request

    new_contact = Contact(
        username=content['username'],
        phonenumber=content['phonenumber'],
        country=content.get('country'),
        state=content.get('state'),
        email=content['email'],
        email_opt_in_status=content['email_opt_in_status'],
        sms_opt_in_status=content['sms_opt_in_status'],
        matm_owner=content['matm_owner'],
        individual_id=content.get('individual_id'),
        status=content.get('status'),
        contact_id=content.get('contact_id')
    )

    message = "Contact added successfully"
    new_contact.contact_id = uuid4().hex[:8]

    new_contact.contact_id = uuid4().hex[:8]
    phone = session.query(ContactPointPhone).filter_by(phonenumber = content['phonenumber']).all()
    email = session.query(ContactPointEmail).filter_by(email = content['email']).all()
    print(type(phone))
    print(type(email))
    matched_contacts = []
    matched_individuals = []
    try:
        for result_email in email:
            if result_email.matm_owner == content['matm_owner'] and result_email.username == content['username']:
                matched_contacts.append(result_email.contact_id)
            elif result_email.matm_owner == content['matm_owner'] and result_email.username != content['username']:
                raise ValueError("matching error on contact data")
            elif result_email.matm_owner != content['matm_owner'] and result_email.username == content['username']:
                matched_individuals.append(result_email.contact_id)

        for result_phone in phone:
            if result_phone.matm_owner == content['matm_owner'] and result_phone.username == content['username']:
                matched_contacts.append(result_phone.contact_id)
            elif result_phone.matm_owner == content['matm_owner'] and result_phone.username != content['username']:
                raise ValueError("matching error on contact data")
            elif result_phone.matm_owner != content['matm_owner'] and result_phone.username == content['username']:
                matched_individuals.append(result_phone.contact_id)

    except Exception as error:
        new_contact.status = message = str(error)
    
    if matched_contacts:
        new_contact = session.query(Contact).filter_by(contact_id = matched_contacts[0]).first()
        new_contact.state = content["state"]
        new_contact.country = content["country"]
        new_contact.status = f"updated - {start_time - time.time()}"
        message = "contact Updated"

    elif matched_individuals:
        individual_id = session.query(Contact.individual_id).filter_by(contact_id = matched_individuals[0]).first()
        new_contact.individual_id == individual_id
        new_contact.status = f"created - {time.time()}"

    if message == "Contact added successfully" or matched_individuals:

        try:
            email_opt_in = ContactPointEmail(
                username=new_contact.username,
                email=new_contact.email,
                country=new_contact.country,
                state=new_contact.state,
                matm_owner = new_contact.matm_owner,
                contact_id = new_contact.contact_id
            )
            session.add(email_opt_in)
        except Exception as e:
            print(e)

        try:
            mobile_opt_in = ContactPointPhone(
                username=new_contact.username,
                phonenumber=new_contact.phonenumber,
                country=new_contact.country,
                state=new_contact.state,
                matm_owner = new_contact.matm_owner,
                contact_id = new_contact.contact_id
            )
            session.add(mobile_opt_in)
        except Exception as e:
            print(e)
        
    
    session.add(new_contact)

    session.commit()
    duration = time.time() - start_time

    return jsonify({'message': message, 'username': content['username'], 'time taken':duration})

@app.route('/contacts/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def contact(id):
    # Get contact by id
    contact = session.query(Contact).filter_by(id=id).first()
    if not contact:
        return jsonify({'message': 'Contact not found'}), 404  # Not found

    if request.method == 'GET':
        # Return contact details
        return jsonify(ContactSchema().dump(contact))

    elif request.method == 'PUT':
        # Update contact
        content = request.get_json()
        schema = ContactSchema()
        # Validate data (excluding id)
        errors = schema.validate(content, partial=True)
        if errors:
            return jsonify(errors), 400  # Bad request

        contact.username = content.get('username', contact.username)
        contact.phonenumber = content.get('phonenumber', contact.phonenumber)
        contact.country = content.get('country', contact.country)
        contact.state = content.get('state', contact.state)
        contact.email = content.get('email', contact.email)
        contact.email_opt_in_status = content.get('email_opt_in_status', contact.email_opt_in_status)
        contact.sms_opt_in_status = content.get('sms_opt_in_status', contact.sms_opt_in_status)
        contact.matm_owner = content.get('matm_owner', contact.matm_owner)
        contact.individual_id = content.get('individual_id', contact.individual_id)
        contact.status = content.get('status', contact.status)
        contact.contact_id = content.get('contact_id', contact.contact_id)
        session.commit()
        return jsonify(schema.dump(contact))

    elif request.method == 'DELETE':
        # Delete contact
        session.delete(contact)
        session.commit()
        return jsonify({'message': 'Contact deleted successfully'})
    
@app.route('/email', methods=['GET'])
def get_email():
    emails = session.query(ContactPointEmail).all()
    return jsonify(email_schema.dump(emails))

@app.route('/mobile', methods=['GET'])
def get_phone():
    mobile = session.query(ContactPointPhone).all()
    return jsonify(mobile_schema.dump(mobile))

@app.route('/individual', methods=['GET'])
def get_individual():
    individual = session.query(ContactPointPhone).all()
    return jsonify(individual_schema.dump(individual))


if __name__ == '__main__':
    app.run(debug=True)