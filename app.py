from flask import Flask, request, jsonify, Response, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_restful import Resource, Api
from sqlalchemy.orm import backref

app = Flask(__name__)

api = Api(app)
app.config['JSON_SORT_KEYS'] = False
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
    userId = db.Column(db.Integer, db.ForeignKey('User.id'))
    user = db.relationship("User", backref=backref("User", uselist=False))
    comment = db.Column(db.String, nullable=False)
    approved = db.Column(db.Boolean, nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    movieId = db.Column(db.Integer, db.ForeignKey('Movie.id'), nullable=False)
    movie = db.relationship("Movie", backref=backref("Movie", uselist=False))


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password', 'role')


class MovieSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'description', 'rating')


class CommentSchema(ma.Schema):
    class Meta:
        fields = ('id', 'userId', 'movieId', 'comment', 'createdAt')


user_schema = UserSchema()
users_schema = UserSchema(many=True)

comments_schema = CommentSchema(many=True)

movies_schema = MovieSchema(many=True)
movie_schema = MovieSchema()


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
def add_movie():
    try:
        body = request.get_json()
        movie_name = body['name']
        movie_description = body['description']
    except:
        return make_response({'message': 'Not Found'}, 404)

    adding_movie = Movie(movie_name, movie_description, 0)
    print(adding_movie)

    db.session.add(adding_movie)
    db.session.commit()
    return make_response(jsonify({"message":"OK"}), 204)



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
