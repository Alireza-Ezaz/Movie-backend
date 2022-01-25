from flask import Flask, request, jsonify, Response, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Resource, Api
from sqlalchemy.orm import backref
from datetime import datetime
from functools import wraps
import jwt

app = Flask(__name__)

api = Api(app)
app.config['JSON_SORT_KEYS'] = False
app.config[
    'SECRET_KEY'] = 'NTNv7j0TuYARvmNMmWXo6fKvM4o6nv/aUi9ryX38ZH+L1bkrnD1ObOQ8JAUmHCBq7Iy7otZcyAagBLHVKvvYaIpmMuxmARQ97jUVG16Jkpkp1wXOPsrF9zwew6TpczyHkHgX5EuLg2MeBuiT/qJACs1J0apruOOJCg/gOtkjB4c='
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movieApp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)


class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True)
    password = db.Column(db.String(32))
    role = db.Column(db.Integer)

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role


class Movie(db.Model):
    __tablename__ = 'Movie'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    rating = db.Column(db.Float)

    def __init__(self, name, description, rating):
        self.name = name
        self.description = description
        self.rating = rating


class Comment(db.Model):
    __tablename__ = 'Comment'
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    userId = db.Column(db.Integer, db.ForeignKey('User.id'))
    user = db.relationship("User", backref=backref("User", uselist=False))
    movieId = db.Column(db.Integer, db.ForeignKey('Movie.id'), nullable=False)
    movie = db.relationship("Movie", backref=backref("Movie", uselist=False))

    def __init__(self, userId, movieId, comment_body):
        self.userId = userId
        self.movieId = movieId
        self.comment = comment_body
        self.createdAt = datetime.now()
        self.approved = 0


class Vote(db.Model):
    __tablename__ = 'Vote'
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Float)
    userId = db.Column(db.Integer, db.ForeignKey('User.id'))
    user = db.relationship("User", backref=backref("User2", uselist=False))
    movieId = db.Column(db.Integer, db.ForeignKey('Movie.id'), nullable=False)
    movie = db.relationship("Movie", backref=backref("Movie2", uselist=False))

    def __init__(self, userId, movieId, rating):
        self.userId = userId
        self.movieId = movieId
        self.rating = rating


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password', 'role')


class MovieSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'description', 'rating')


class CommentSchema(ma.Schema):
    class Meta:
        fields = ('id', 'userId', 'movieId', 'comment', 'createdAt')


class VoteSchema(ma.Schema):
    class Meta:
        fields = ('id', 'userId', 'movieId', 'rating')


user_schema = UserSchema()
users_schema = UserSchema(many=True)

comments_schema = CommentSchema(many=True)

movies_schema = MovieSchema(many=True)
movie_schema = MovieSchema()


def check_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
            print(token)
        # return 401 if token is not passed
        if not token:
            return jsonify({'message': 'You do NOT have access !'}), 401

        try:
            # decoding the payload to fetch the stored details
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            print(data)
            current_user = User.query \
                .filter_by(id=data['userId']) \
                .first()
            # current_user = User.query.get(data['userId'])
            print(current_user)

        except:
            return jsonify({
                'message': 'Token is invalid !'
            }), 401
        # returns the current logged in users contex to the routes
        return f(current_user, *args, **kwargs)

    return decorated


@app.route("/movies")
def get_movies():
    try:
        movies = Movie.query.all()
        return make_response(jsonify(movies_schema.dump(movies)), 200)
    except Exception as ex:
        return make_response({'message': 'There is an internal issue.'}, 500)


@app.route("/movie/<movie_id>")
def get_movie(movie_id):
    try:
        movieId = movie_id
        movie = Movie.query.get(movieId)
        if (movie == None):
            return make_response({'message': 'Bad request'}, 400)
        return make_response(jsonify(movie_schema.dump(movie)), 200)
    except Exception as ex:
        return make_response({'message': 'There is an internal issue.'}, 500)


@app.route("/comments")
def get_comments():
    try:
        try:
            movie_id = request.args['movie']
        except Exception as _:
            movie_id = None
            return make_response({'message': 'Bad Request'}, 400)

        movie = Movie.query.get(movie_id)
        if movie == None:
            return make_response({'message': 'Not Found'}, 404)

        comments_db = Comment.query. \
            join(User, Comment.userId == User.id) \
            .add_columns(User.username, Comment.id, Comment.comment, Comment.movieId, Comment.approved) \
            .filter(Comment.movieId == movie_id)
        comments = []
        for comment in comments_db:
            if comment.approved:
                comments.append({
                    "id": comment.id,
                    "author": comment.username,
                    "body": comment.comment
                })
        return make_response(jsonify({
            "movie": movie.name,
            "comments": comments
        }), 200)

    except Exception as ex:
        return make_response({'message': 'There is an internal issue.'}, 500)


@app.route("/admin/movie", methods=['POST'])
@check_token
def add_movie(current_user):
    if current_user.role != 1:
        return jsonify({'message': 'Only admin can do this !'}), 401
    try:
        body = request.get_json()
        movie_name = body['name']
        movie_description = body['description']
    except:
        return make_response({'message': 'Not Found'}, 404)

    adding_movie = Movie(movie_name, movie_description, None)
    print(adding_movie)

    db.session.add(adding_movie)
    db.session.commit()
    return make_response(jsonify({"message": "OK"}), 204)


@app.route("/admin/movie/<movie_id>", methods=['PUT'])
@check_token
def edit_movie(current_user, movie_id):
    if current_user.role != 1:
        return jsonify({'message': 'Only admin can do this !'}), 401
    try:
        body = request.get_json()
        movie_name = body['name']
        movie_description = body['description']
    except:
        return make_response({'message': 'Bad request.'}, 400)
    if not movie_id.isnumeric():
        return make_response({'message': 'Bad request.'}, 400)
    movie = Movie.query.filter_by(id=movie_id).first()
    if movie == None:
        return make_response({'message': 'Bad request.'}, 400)
    movie.name = movie_name
    movie.description = movie_description
    db.session.commit()
    return make_response(jsonify({"message": "OK"}), 204)


@app.route("/admin/movie/<movie_id>", methods=['DELETE'])
@check_token
def remove_movie(current_user, movie_id):
    if current_user.role != 1:
        return jsonify({'message': 'Only admin can do this !'}), 401
    try:
        if not movie_id.isnumeric():
            return make_response({'message': 'Bad request.'}, 400)
        removing_movie = Movie.query.get(movie_id)
        if removing_movie == None:
            return make_response({'message': 'Bad request.'}, 400)
        Movie.query.filter_by(id=movie_id).delete()
        db.session.commit()
        return make_response(jsonify({"message": "OK"}), 204)
    except:
        return make_response({'message': 'There was an internal issue.'}, 500)


@app.route("/admin/comment/<comment_id>", methods=['PUT'])
@check_token
def edit_comment(current_user, comment_id):
    if current_user.role != 1:
        return jsonify({'message': 'Only admin can do this !'}), 401
    try:
        body = request.get_json()
        approved = body['approved']
    except:
        return make_response({'message': 'Bad request.'}, 400)
    if not comment_id.isnumeric():
        return make_response({'message': 'Bad request.'}, 400)
    comment = Comment.query.filter_by(id=comment_id).first()
    if (comment == None) or (type(approved) != type(False)):
        return make_response({'message': 'Bad request.'}, 400)
    comment.approved = approved
    db.session.commit()
    return make_response(jsonify({"message": "OK"}), 204)


@app.route("/admin/comment/<comment_id>", methods=['DELETE'])
@check_token
def remove_comment(current_user, comment_id):
    if current_user.role != 1:
        return jsonify({'message': 'Only admin can do this !'}), 401
    try:
        if not comment_id.isnumeric():
            return make_response({'message': 'Bad request.'}, 400)
        removing_comment = Comment.query.get(comment_id)
        if removing_comment == None:
            return make_response({'message': 'Bad request.'}, 400)
        Comment.query.filter_by(id=comment_id).delete()
        db.session.commit()
        return make_response(jsonify({"message": "OK"}), 204)
    except:
        return make_response({'message': 'There was an internal issue.'}, 500)


class UserManager(Resource):
    @staticmethod
    def get():
        try:
            id = request.args['id']
        except Exception as _:
            id = None

        if not id:
            users = User.query.all()
            return jsonify(users_schema.dump(users))
        user = User.query.get(id)
        return jsonify(user_schema.dump(user))

    @staticmethod
    def post():
        username = request.json['username']
        password = request.json['password']
        role = request.json['role']

        user = User(username, password, role)
        db.session.add(user)
        db.session.commit()
        return jsonify({
            'Message': f'User {username} inserted.'
        })

    @staticmethod
    def put():
        try:
            id = request.args['id']
        except Exception as _:
            id = None
        if not id:
            return jsonify({'Message': 'Must provide the user ID'})
        user = User.query.get(id)

        username = request.json['username']
        password = request.json['password']
        role = request.json['role']

        user.username = username
        user.password = password
        user.role = role

        db.session.commit()
        return jsonify({
            'Message': f'User {username} altered.'
        })

    @staticmethod
    def delete():
        try:
            id = request.args['id']
        except Exception as _:
            id = None
        if not id:
            return jsonify({'Message': 'Must provide the user ID'})
        user = User.query.get(id)

        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'Message': f'User {str(id)} deleted.'
        })


api.add_resource(UserManager, '/api/users')

if __name__ == '__main__':
    app.run(debug=True)
