from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Resource, Api




app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"
