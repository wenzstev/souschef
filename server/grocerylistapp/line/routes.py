from flask import Blueprint, request, jsonify, g

from sqlalchemy.exc import IntegrityError

from grocerylistapp import db
from grocerylistapp.models import RecipeLine, Recipe
from grocerylistapp.utils import get_resource_or_404, put_resource, post_new_resource
from grocerylistapp.errors.exceptions import InvalidUsage

from grocerylistapp.line.schemas import RecipeLineSchema, RecipelineIngredientAssociationSchema
from grocerylistapp.line.utils import get_new_ingredients_on_line, get_line_by_params
from grocerylistapp.ingredient.schemas import IngredientSchema

line = Blueprint("line", __name__)
recipeline_schema = RecipeLineSchema()
recipelines_schema = RecipeLineSchema(many=True)
ingredients_schema = IngredientSchema(many=True)
recipeline_association_schema = RecipelineIngredientAssociationSchema(many=True)


@line.route("/api/lines", methods=['GET'])
def get_lines_by_params():
    lines = get_line_by_params(request.args)
    return jsonify(recipelines_schema.dump(lines))

@line.route("/api/lines/<int:id_>", methods=['GET'])
def get_line(id_):
    current_line = get_resource_or_404(RecipeLine, id_)
    return jsonify(recipeline_schema.dump(current_line))


@line.route("/api/lines", methods=['POST'])
@auth.login_required
def post_line():
    recipe_to_add_line = get_resource_or_404(Recipe, request.json.get("recipe_id"))
    if recipe_to_add_line.creator_id == g.user.id:
        new_line = post_new_resource(RecipeLine, request.json)
        return jsonify(recipeline_schema.dump(new_line))
    else:
        raise InvalidUsage("You don't have permission to modify that recipe.")

# FIXME: this is currently broken after the changes to RecipeLines in the model
@line.route("/api/lines/<int:id_>", methods=['PUT'])
@auth.login_required
def put_line(id_):
    line_to_change = get_resource_or_404(RecipeLine, id_)
    if g.user.id == line_to_change.recipe.creator_id:
        line_to_change.text = request.json.get("text", "")
        line_to_change.ingredients = ingredients_schema.load(request.json.get("ingredients", ""))
        db.session.commit()
        return jsonify(recipeline_schema.dump(line_to_change))
    else:
        raise InvalidUsage("You don't have permission to modify that line.", 401)


@line.route('/api/lines/<int:id_>/ingredients', methods=['PUT'])
@auth.login_required
def change_ingredients_in_line(id_):
    line_to_change = get_resource_or_404(RecipeLine, id_)

    logged_in = hasattr(g, 'user')

    def change_line():
        new_ingredients_json = request.json.get("new_ingredients")
        print(new_ingredients_json)
        new_ingredients = get_new_ingredients_on_line(new_ingredients_json, line_to_change)
        print(new_ingredients)
        line_to_change.ingredients = recipeline_association_schema.loads(new_ingredients)
        print(line_to_change)
        db.session.commit()
        return jsonify(recipeline_schema.dump(line_to_change))

    if not line_to_change.recipe.creator_id: # anonymously created
        return change_line()

    print(logged_in, g.user)

    if logged_in and g.user.id == line_to_change.recipe.creator_id:
        return change_line()
    else:
        raise InvalidUsage("You don't have permission to modify that line.", 401)


@line.route("/api/lines/<int:id_>", methods=["DELETE"])
def delete_line(id_):
    line_to_delete = get_resource_or_404(RecipeLine, id_)

    if not line_to_delete.recipe.creator_id or hasattr(g, 'user') and g.user.id == line_to_delete.recipe.creator_id:
        db.session.delete(line_to_delete)
        db.session.commit()
        return ('', 204)
    else:
        return ('', 403)