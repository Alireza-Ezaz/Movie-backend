

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True)
    role = db.Column(db.Integer)
    password = db.Column(db.String(32))

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role