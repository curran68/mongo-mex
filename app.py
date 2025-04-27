import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for
)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from werkzeug.utils import secure_filename

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_recipes")
def get_recipes():
    """
    Retrieves all recipes from the database and renders the recipes.html
    template.
    """
    recipes = list(mongo.db.recipes.find())
    return render_template("recipes.html", recipes=recipes)


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles user registration.  If the method is POST, it validates the
    username, checks for duplicates, hashes the password, and stores the
    new user in the database.  If the method is GET, it renders the
    registration form.
    """
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()}
        )

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register_data = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(
                request.form.get("password")
            ),
        }
        mongo.db.users.insert_one(register_data)
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login. If the method is POST, it retrieves the user
    from the database, verifies the password, and sets the user session.
    If the method is GET, it renders the login form.
    """
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()}
        )

        if existing_user:
            if check_password_hash(
                existing_user["password"], request.form.get("password")
            ):
                session["user"] = request.form.get("username").lower()
                flash(f"Welcome, {request.form.get('username')}")
                return redirect(
                    url_for("profile", username=session["user"])
                )
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

        flash("Incorrect Username and/or Password")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    """
    Displays the user's profile information.

    Args:
        username (str): The username of the user whose profile is
            being displayed.
    """
    user_name = mongo.db.users.find_one(
        {"username": session["user"]}
    )["username"]
    return render_template("profile.html", username=user_name)


@app.route("/logout")
def logout():
    """
    Logs the user out by removing the user session and redirects to
    the login page.
    """
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    """
    Handles adding a new recipe. If the method is POST, it processes
    the form data, including image upload, and inserts the new recipe
    into the database. If the method is GET, it renders the add_recipe
    form.
    """
    if request.method == "POST":
        recipe_image = request.files.get("recipe_image")
        image_filename = None
        if recipe_image and recipe_image.filename != "":
            image_filename = secure_filename(recipe_image.filename)
            recipe_image.save(os.path.join("static/images", image_filename))

        recipe_data = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_ingredients": request.form.get(
                "recipe_ingredients").split("\n"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_cooktime": request.form.get("recipe_cooktime"),
            "created_by": session["user"],
            "image_filename": image_filename,
        }

        mongo.db.recipes.insert_one(recipe_data)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    courses = mongo.db.courses.find().sort("recipe_course", 1)
    return render_template("add_recipe.html", courses=courses)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    """
    Handles editing an existing recipe. If the method is POST, it
    processes the form data, including image upload, and updates the
    recipe in the database. If the method is GET, it retrieves the
    recipe data and renders the edit_recipe form.

    Args:
        recipe_id (str): The unique ID of the recipe to be edited.
    """
    if request.method == "POST":
        recipe_image = request.files.get("recipe_image")
        image_filename = None
        if recipe_image and recipe_image.filename != "":
            image_filename = secure_filename(recipe_image.filename)
            recipe_image.save(os.path.join("static/images", image_filename))

        recipe_data = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_ingredients": request.form.get(
                "recipe_ingredients").split("\n"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_cooktime": request.form.get("recipe_cooktime"),
            "created_by": session["user"],
            "image_filename": image_filename,
        }

        mongo.db.recipes.update_one(
            {"_id": ObjectId(recipe_id)}, {"$set": recipe_data}
        )
        flash("Recipe Successfully Updated")
        return redirect(url_for("get_recipes"))

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    courses = mongo.db.courses.find().sort("recipe_course", 1)
    return render_template("edit_recipe.html", recipe=recipe, courses=courses)


@app.route("/delete_recipe/<recipe_id>", methods=["GET", "POST"])
def delete_recipe(recipe_id):
    """
    Handles deleting a recipe.  Verifies that the user is logged in
    and that the recipe exists and belongs to the user before deleting it.

    Args:
        recipe_id (str): The unique ID of the recipe to be deleted.
    """
    if "user" not in session:
        flash("You need to be logged in to delete recipes")
        return redirect(url_for("login"))

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    if not recipe:
        flash("Recipe not found")
        return redirect(url_for("get_recipes"))

    if recipe["created_by"] != session["user"]:
        flash("You can only delete your own recipes")
        return redirect(url_for("get_recipes"))

    mongo.db.recipes.delete_one({"_id": ObjectId(recipe_id)})
    flash("Recipe successfully deleted")
    return redirect(url_for("get_recipes"))


if __name__ == "__main__":
    app.run(
        host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=False,
    )