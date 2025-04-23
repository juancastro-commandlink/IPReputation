from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
import time

# Initialize SQLAlchemy (linked in app.py)
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # MD5 hash
    is_admin = db.Column(db.Boolean, default=False)


class IPRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), index=True)
    timestamp = db.Column(db.Float, default=time.time)

class DriverResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), index=True)
    driver = db.Column(db.String(64), index=True)
    data = db.Column(JSON)
    timestamp = db.Column(db.Float, default=time.time)

class DriverConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    include_keys = db.Column(JSON, default=list)  # Keys to include in response

class IPAccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(255))
    timestamp = db.Column(db.Float)
    source = db.Column(db.String(50))  # 'cache' or 'driver'