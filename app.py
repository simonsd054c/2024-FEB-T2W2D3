from datetime import timedelta

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# connect to database                     dbms     db_driver db_user  db_pass   URL     PORT db_name
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://feb_dev:123456@localhost:5432/feb_db"

app.config["JWT_SECRET_KEY"] = "secret"

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Model - table
class Product(db.Model):
    # define the tablename
    __tablename__ = "products"
    # define the primary key
    id = db.Column(db.Integer, primary_key=True)
    # more attributes (columns)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String)
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


# Schema
class ProductSchema(ma.Schema):
    class Meta:
        # fields
        fields = ( "id", "name", "description", "price", "stock" )


# to handle multiple products
products_schema = ProductSchema(many=True)

# to handle a single product
product_schema = ProductSchema()


class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "email", "password", "is_admin")


users_schema = UserSchema(many=True, exclude=["password"])


user_schema = UserSchema(exclude=["password"])


# CLI Commands
@app.cli.command("create")
def create_tables():
    db.create_all()
    print("Tables created")


@app.cli.command("seed")
def seed_tables():
    # create a product object
    product1 = Product(
        name="Product 1",
        description="Product 1 description",
        price=479.99,
        stock=15
    )

    product2 = Product()
    product2.name = "Product 2"
    product2.price = 15.99
    product2.stock = 24

    # products = [product1, product2]
    # db.session.add_all(products)

    # add to session
    db.session.add(product1)
    db.session.add(product2)


    users = [
        User(
            name="User 1",
            email="user1@email.com",
            password=bcrypt.generate_password_hash("123456").decode('utf8')
        ),
        User(
            email="admin@email.com",
            password=bcrypt.generate_password_hash("123456").decode('utf8'),
            is_admin=True
        )
    ]

    db.session.add_all(users)

    # commit
    db.session.commit()

    print("Tables seeded")


@app.cli.command("drop")
def drop_tables():
    db.drop_all()
    print("Tables dropped")



# /products, GET => gettting all products
# /products/id, GET => get a single product whose id is equal to the one in the url
# /products, POST => create a new product
# /products/id, PUT/PATCH => Edit/Update the product whose id is equal to the one in the url
# /products/id, DELETE => Delete the product whose id is equal to the one in the url



@app.route("/products")
def get_products():
    # SELECT * FROM products
    stmt = db.select(Product) # Result # [[]]
    products_list = db.session.scalars(stmt) # ScalarResult # []
    data = products_schema.dump(products_list)
    return data


@app.route("/products/<int:product_id>")
def get_product(product_id):
    stmt = db.select(Product).filter_by(id=product_id)
    product = db.session.scalar(stmt)
    if product:
        data = product_schema.dump(product)
        return data
    else:
        return {"error": f"Product with id {product_id} doesn't exist"}, 404
    

@app.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    product_fields = request.get_json()
    new_product = Product(
        name=product_fields.get("name"),
        description=product_fields.get("description"),
        price=product_fields.get("price"),
        stock=product_fields.get("stock")
    )
    db.session.add(new_product)
    db.session.commit()
    return product_schema.dump(new_product), 201


@app.route("/products/<int:product_id>", methods=["PUT", "PATCH"])
def update_product(product_id):
    # find the product from the db with the id product_id
    stmt = db.select(Product).filter_by(id=product_id)
    product = db.session.scalar(stmt)
    # retrieve the data from the body of the request
    body_data = request.get_json()
    if product:
        # update the attributes
        product.name = body_data.get("name") or product.name
        product.description = body_data.get("description") or product.description
        product.price = body_data.get("price") or product.price
        product.stock = body_data.get("stock") or product.stock
        # commit
        db.session.commit()
        # return something
        return product_schema.dump(product)
    else:
        return {"error": f"Product with id {product_id} doesn't exist"}, 404
    

@app.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):

    is_admin = authoriseAsAdmin()
    if not is_admin:
        return {"error": "Not authorised to delete a product"}, 403

    stmt = db.select(Product).where(Product.id==product_id)
    product = db.session.scalar(stmt)
    if product:
        db.session.delete(product)
        db.session.commit()
        return {"message": f"Product with id {product_id} has been deleted"}
    else:
        return {"error": f"Product with id {product_id} doesn't exist"}, 404
    

@app.route("/auth/register", methods=["POST"])
def register_user():
    try:
        # body of the request - data of the user
        body_data = request.get_json()
        # extracting password from the body of the request
        password = body_data.get("password")
        # hashing the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf8')
        # create a user using the User model
        user = User(
            name=body_data.get("name"),
            email=body_data.get("email"),
            password=hashed_password
        )
        # add it to the db session
        db.session.add(user)
        # commit
        db.session.commit()
        # return something back to the user
        return user_schema.dump(user), 201
    except IntegrityError:
        return {"error": "Email address already exists"}, 409
    

@app.route("/auth/login", methods=["POST"])
def login_user():
    # get the data from the body of the request
    body_data = request.get_json()
    # find the user with that email
    # SELECT * FROM user WHERE email='user1@email.com'
    stmt = db.select(User).filter_by(email=body_data.get("email"))
    user = db.session.scalar(stmt)
    # if the user exists and the password matches
    if user and bcrypt.check_password_hash(user.password, body_data.get("password")):
        # create the jwt token
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=1))
        # return the token
        return {"token": token, "email": user.email, "is_admin": user.is_admin}
    
    # else
    else:
        # return an error message
        return {"error": "Invalid email or password"}, 401


def authoriseAsAdmin():
    # get the id of the user from jwt token
    user_id = get_jwt_identity()
    # find the user in the db with that id
    stmt = db.select(User).filter_by(id=user_id)
    user = db.session.scalar(stmt)
    # check whether the user is an admin or not
    return user.is_admin