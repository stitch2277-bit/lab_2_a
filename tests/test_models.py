from decimal import Decimal

import pytest

from main import demo_recipe
from recipes.models import Burger, Ingredient, Pizza, Recipe, Wok, number
from recipes.reports import formatted


@pytest.mark.parametrize("kind,grams,calories,cost,portion_calories,portion_cost", [
    ("pizza", "400", "870", "150", "435", "75"),
    ("wok", "500", "600", "122.5", "300", "61.25"),
    ("burger", "230", "470.5", "100", "470.5", "100"),
])
def test_hand_calculated_examples(kind, grams, calories, cost, portion_calories, portion_cost):
    recipe = demo_recipe(kind)
    assert recipe.total_grams == Decimal(grams)
    assert recipe.total_calories == Decimal(calories)
    assert recipe.total_cost == Decimal(cost)
    result = recipe.snapshot()
    assert Decimal(result["portion_calories"]) == Decimal(portion_calories)
    assert Decimal(result["portion_cost"]) == Decimal(portion_cost)


def test_calories_per_100g_and_portion_weight():
    result = demo_recipe().snapshot()
    assert Decimal(result["kcal_per_100g"]) == Decimal("217.5")
    assert Decimal(result["portion_grams"]) == Decimal("200")


def test_no_rounding_before_summing():
    recipe = Pizza("Точность", 1, [Ingredient("Продукт", 1, 0, "0.49") for _ in range(3)])
    assert recipe.total_cost == Decimal("0.0147")
    assert formatted(recipe.total_cost) == "0.01"
    assert formatted("0.005") == "0.01"


def test_comma_zero_and_unit_conversion():
    ingredient = Ingredient("Вода", "12,5", 0, "0,4")
    assert ingredient.grams == Decimal("12.5")
    assert ingredient.cost == Decimal("0.05")
    assert ingredient.calories == 0


@pytest.mark.parametrize("invalid", ["", "abc", "NaN", "sNaN", "Infinity", "-Infinity", "1e100", "1e-100", "-1", "1.00001", "1." + "0" * 40 + "1", "1" * 101, True, None])
def test_reject_invalid_numbers(invalid):
    with pytest.raises(ValueError):
        number(invalid, "Число")


@pytest.mark.parametrize("value", [0, "0", "0,0", "-0"])
def test_weight_must_be_positive(value):
    with pytest.raises(ValueError):
        Ingredient("Продукт", value, 20, 30)


@pytest.mark.parametrize("value", [0, -1, 1.5, "2", True, 1001])
def test_portions_validation(value):
    with pytest.raises(ValueError):
        Pizza("Тест", value, [Ingredient("Сыр", 100, 350, 80)])


@pytest.mark.parametrize("name", ["", "  ", None, "x" * 101, "x\ny"])
def test_invalid_names(name):
    with pytest.raises(ValueError):
        Ingredient(name, 100, 350, 80)


def test_managed_attributes_validate_on_assignment():
    ingredient = Ingredient("Сыр", 100, 350, 80)
    recipe = Pizza("Тест", 1, [ingredient])
    ingredient.grams = 200
    recipe.portions = 2
    assert recipe.total_cost == 160
    assert Decimal(recipe.snapshot()["portion_cost"]) == 80
    with pytest.raises(ValueError):
        ingredient.grams = -1
    assert ingredient.grams == 200
    with pytest.raises(ValueError):
        recipe.portions = 0
    with pytest.raises(ValueError):
        ingredient.price_per_100g = -1
    with pytest.raises(ValueError):
        ingredient.kcal_per_100g = "NaN"


def test_recipe_is_abstract():
    with pytest.raises(TypeError):
        Recipe("Тест", 1, [Ingredient("Сыр", 100, 350, 80)])


def test_empty_recipe_and_wrong_ingredient():
    with pytest.raises(ValueError):
        Pizza("Тест", 1, [])
    with pytest.raises(TypeError):
        Pizza("Тест", 1, ["не ингредиент"])


@pytest.mark.parametrize("recipe_class,label", [(Wok, "Вок"), (Burger, "Бургер"), (Pizza, "Пицца")])
def test_inheritance_and_dunder_methods(recipe_class, label):
    ingredient = Ingredient("Тест", 1, 1, 1)
    recipe = recipe_class("Пример", 1, [ingredient])
    assert isinstance(recipe, Recipe)
    assert len(recipe) == 1
    assert label in str(recipe)
    assert "Тест" in str(ingredient)
    assert "Ingredient" in repr(ingredient)


def test_snapshot_is_independent():
    recipe = demo_recipe()
    result = recipe.snapshot()
    recipe.ingredients[0].grams = 1
    assert result["ingredients"][0]["grams"] == "200"


def test_limits_and_trailing_zeros():
    assert number("1000000", "Число") == Decimal("1000000")
    assert number("1.23000", "Число") == Decimal("1.23")
    with pytest.raises(ValueError):
        number("1000000.01", "Число")
