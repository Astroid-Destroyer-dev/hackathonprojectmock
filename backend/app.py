from flask import Flask, jsonify, request, session, render_template
import os
from modules.sqlalchemy import db
from dotenv import load_dotenv
from flask_restx import Api, Resource, fields, Namespace

load_dotenv()
app = Flask(__name__)
# fallback secret for dev
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(BASE_DIR, "todo.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# import models after db.init_app to avoid circular import
from models.user import User

# initialize API docs
api = Api(app, title="My API", version="1.0", doc="/docs")  # docs available at /docs

# Namespaces
auth_ns = Namespace("auth", description="Authentication endpoints")
admin_ns = Namespace("admin", description="Admin endpoints")
list_ns = Namespace("List",description="List things")

# Models for Swagger
login_model = auth_ns.model("Login", {
    "username": fields.String(required=True),
    "password": fields.String(required=True),
})

create_user_model = admin_ns.model("CreateUser", {
    "username": fields.String(required=True),
    "password": fields.String(required=True),
    "role": fields.String(required=False),
})


@auth_ns.route("/login")
class Login(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        data = api.payload or {}
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return {"ok": False, "error": "Enter username and password"}, 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return {"ok": False, "error": "Invalid credentials"}, 401

        session['user_id'] = user.id
        return {"ok": True, "username": username}, 200

@admin_ns.route("/init_admin")
class InitAdmin(Resource):
    @admin_ns.expect(create_user_model)
    def post(self):
        data = api.payload or {}
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return {"ok": False, "error": "Enter username and password"}, 400
        if User.query.filter_by(username=username).first():
            return {"ok": False, "error": "username taken"}, 409

        user = User(username=username, admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return {"ok": True, "message": "Admin init successfully", "username": username}, 201

@admin_ns.route("/create_user")
class CreateUser(Resource):
    @admin_ns.expect(create_user_model)
    def post(self):
        user_id = session.get('user_id')
        if not user_id:
            return {"ok": False, "error": "Authentication required"}, 401

        current_user = User.query.get(user_id)
        if not current_user or not getattr(current_user, "admin", False):
            return {"ok": False, "error": "Admin privileges required"}, 403

        data = api.payload or {}
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")

        if not username or not password:
            return {"ok": False, "error": "username and password required"}, 400
        if User.query.filter_by(username=username).first():
            return {"ok": False, "error": "username taken"}, 409

        new_user = User(username=username, role=role, admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return {"ok": True, "username": username}, 201

# register namespaces with the Api
api.add_namespace(auth_ns, path="/auth")
api.add_namespace(admin_ns, path="/admin")
api.add_namespace(list_ns,path="/list")

@app.route("/")
def index():
    return render_template("index.html")

@list_ns.route("/list_user")
class ListUser(Resource):
    @list_ns.doc("list_users")
    def get(self):
        users = User.query.all()
        result = [
            {"id": u.id, "username": u.username, "admin": bool(u.admin), "role": u.role}
            for u in users
        ]
        return {"ok": True, "users": result}, 200

if __name__ == "__main__":
    # run with debug True for development
    app.run(debug=True)

