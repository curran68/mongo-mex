import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
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
    recipes = list(mongo.db.recipes.find())
    return render_template("recipes.html", recipes=recipes)
    

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                        session["user"] = request.form.get("username").lower()
                        flash("Welcome, {}".format(
                            request.form.get("username")))
                        return redirect(url_for(
                            "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    return render_template("profile.html", username=username)


@app.route("/logout")
def logout():
    # remove user from session cookie
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        # Handle image upload
        recipe_image = request.files.get("recipe_image")
        image_filename = None
        if recipe_image and recipe_image.filename != "":
            image_filename = secure_filename(recipe_image.filename)
            recipe_image.save(os.path.join("static/images", image_filename))

        # Create recipe dictionary
        recipe = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_ingredients": request.form.get("recipe_ingredients").split("\n"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_cooktime": request.form.get("recipe_cooktime"),
            "created_by": session["user"],
            "image_filename": image_filename  # Save filename in database
        }
 
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe Successfully Added")
        return redirect(url_for("get_recipes"))

    courses = mongo.db.courses.find().sort("recipe_course", 1)
    return render_template("add_recipe.html", courses=courses)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    courses = mongo.db.courses.find().sort("recipe_course", 1)
    if request.method == "POST":
        # Handle image upload
        recipe_image = request.files.get("recipe_image")
        image_filename = None
        if recipe_image and recipe_image.filename != "":
            image_filename = secure_filename(recipe_image.filename)
            recipe_image.save(os.path.join("static/images", image_filename))

        # Create recipe dictionary
        recipe = {
            "recipe_name": request.form.get("recipe_name"),
            "recipe_ingredients": request.form.get("recipe_ingredients").split("\n"),
            "recipe_servings": request.form.get("recipe_servings"),
            "recipe_cooktime": request.form.get("recipe_cooktime"),
            "created_by": session["user"],
            "image_filename": image_filename  # Save filename in database
        }

        # Update the recipe in MongoDB
        mongo.db.recipes.update_one({"_id": ObjectId(recipe_id)}, {"$set": recipe})
        flash("Recipe Successfully Updated")
        return redirect(url_for("get_recipes"))

    # Get the recipe from MongoDB
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    courses = mongo.db.courses.find().sort("recipe_course", 1)
    return render_template("edit_recipe.html", recipe=recipe, courses=courses)

@app.route("/delete_recipe/<recipe_id>", methods=["GET", "POST"])
def delete_recipe(recipe_id):
    # Check if user is logged in
    if "user" not in session:
        flash("You need to be logged in to delete recipes")
        return redirect(url_for("login"))

    # Get the recipe from MongoDB
    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})

    # Check if recipe exists and belongs to the current user
    if not recipe:
        flash("Recipe not found")
        return redirect(url_for("get_recipes"))
    
    if recipe["created_by"] != session["user"]:
        flash("You can only delete your own recipes")
        return redirect(url_for("get_recipes"))

    # Delete the recipe
    mongo.db.recipes.delete_one({"_id": ObjectId(recipe_id)})
    flash("Recipe successfully deleted")
    return redirect(url_for("get_recipes"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)