from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

app = Flask(__name__)

# connect to database                     dbms     db_driver db_user  db_pass   URL     PORT db_name
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://feb_dev:123456@localhost:5432/feb_db"

db = SQLAlchemy(app)
ma = Marshmallow(app)

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

# Schema
class ProductSchema(ma.Schema):
    class Meta:
        # fields
        fields = ( "id", "name", "description", "price", "stock" )


# to handle multiple products
products_schema = ProductSchema(many=True)

# to handle a single product
product_schema = ProductSchema()


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
def delete_product(product_id):
    stmt = db.select(Product).where(Product.id==product_id)
    product = db.session.scalar(stmt)
    if product:
        db.session.delete(product)
        db.session.commit()
        return {"message": f"Product with id {product_id} has been deleted"}
    else:
        return {"error": f"Product with id {product_id} doesn't exist"}, 404