"""Предметная модель и расчёты без ввода, файлов и базы данных."""

from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation


def number(value, label, *, positive=False):
    """Проверить число; запятая и точка допускаются как разделитель."""
    try:
        if isinstance(value, bool):
            raise ValueError
        raw = str(value).strip().replace(",", ".")
        if len(raw) > 100:
            raise ValueError
        result = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label}: введите число.") from None
    if not result.is_finite():
        raise ValueError(f"{label}: число должно быть конечным.")
    if result < 0 or (positive and result == 0):
        relation = "больше нуля" if positive else "не меньше нуля"
        raise ValueError(f"{label}: значение должно быть {relation}.")
    if result > 1_000_000:
        raise ValueError(f"{label}: допустимо значение до 1000000.")
    if not result:
        return Decimal(0)
    digits = list(result.as_tuple().digits)
    exponent = result.as_tuple().exponent
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    if exponent < -4:
        raise ValueError(f"{label}: допускается до 4 знаков после запятой.")
    return result


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: название не может быть пустым.")
    result = value.strip()
    if len(result) > 100 or any(ord(char) < 32 for char in result):
        raise ValueError(f"{label}: до 100 символов без управляющих символов.")
    return result


class Ingredient:
    """Масса в граммах, калорийность и цена именно на 100 г."""

    def __init__(self, name, grams, kcal_per_100g, price_per_100g):
        self.name = name
        self.grams = grams
        self.kcal_per_100g = kcal_per_100g
        self.price_per_100g = price_per_100g

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = text(value, "Ингредиент")

    @property
    def grams(self):
        return self._grams

    @grams.setter
    def grams(self, value):
        self._grams = number(value, "Масса, г", positive=True)

    @property
    def kcal_per_100g(self):
        return self._kcal_per_100g

    @kcal_per_100g.setter
    def kcal_per_100g(self, value):
        self._kcal_per_100g = number(value, "Ккал на 100 г")

    @property
    def price_per_100g(self):
        return self._price_per_100g

    @price_per_100g.setter
    def price_per_100g(self, value):
        self._price_per_100g = number(value, "Цена на 100 г")

    @property
    def calories(self):
        return self.grams * self.kcal_per_100g / 100

    @property
    def cost(self):
        return self.grams * self.price_per_100g / 100

    def __str__(self):
        return f"{self.name}: {self.grams} г"

    def __repr__(self):
        return (f"Ingredient({self.name!r}, {str(self.grams)!r}, "
                f"{str(self.kcal_per_100g)!r}, {str(self.price_per_100g)!r})")


class Recipe(ABC):
    """Общий алгоритм для разных блюд; напрямую создать Recipe нельзя."""

    def __init__(self, name, portions, ingredients):
        self.name = name
        self.portions = portions
        items = tuple(ingredients)
        if not items or len(items) > 1000:
            raise ValueError("Нужно от 1 до 1000 ингредиентов.")
        if not all(isinstance(item, Ingredient) for item in items):
            raise TypeError("В рецепте допустимы только объекты Ingredient.")
        self._ingredients = items

    @property
    @abstractmethod
    def kind(self):
        """Тип блюда, который обязан определить класс-наследник."""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = text(value, "Рецепт")

    @property
    def portions(self):
        return self._portions

    @portions.setter
    def portions(self, value):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1000:
            raise ValueError("Количество порций: целое число от 1 до 1000.")
        self._portions = value

    @property
    def ingredients(self):
        return self._ingredients

    @property
    def total_grams(self):
        return sum((item.grams for item in self.ingredients), Decimal(0))

    @property
    def total_calories(self):
        return sum((item.calories for item in self.ingredients), Decimal(0))

    @property
    def total_cost(self):
        return sum((item.cost for item in self.ingredients), Decimal(0))

    def snapshot(self):
        """Независимый снимок; Decimal хранится строкой без потери точности."""
        return {
            "kind": self.kind, "name": self.name, "portions": self.portions,
            "ingredients": [
                {"name": item.name, "grams": str(item.grams),
                 "kcal_per_100g": str(item.kcal_per_100g),
                 "price_per_100g": str(item.price_per_100g),
                 "calories": str(item.calories), "cost": str(item.cost)}
                for item in self.ingredients
            ],
            "total_grams": str(self.total_grams),
            "total_calories": str(self.total_calories),
            "total_cost": str(self.total_cost),
            "portion_grams": str(self.total_grams / self.portions),
            "portion_calories": str(self.total_calories / self.portions),
            "portion_cost": str(self.total_cost / self.portions),
            "kcal_per_100g": str(self.total_calories * 100 / self.total_grams),
        }

    def __len__(self):
        return len(self.ingredients)

    def __str__(self):
        return f"{self.kind} «{self.name}», порций: {self.portions}"


class Wok(Recipe):
    def __init__(self, name, portions, ingredients):
        super().__init__(name, portions, ingredients)

    @property
    def kind(self):
        return "Вок"

    def __str__(self):
        return super().__str__()


class Burger(Recipe):
    def __init__(self, name, portions, ingredients):
        super().__init__(name, portions, ingredients)

    @property
    def kind(self):
        return "Бургер"

    def __str__(self):
        return super().__str__()


class Pizza(Recipe):
    def __init__(self, name, portions, ingredients):
        super().__init__(name, portions, ingredients)

    @property
    def kind(self):
        return "Пицца"

    def __str__(self):
        return super().__str__()
