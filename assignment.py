# Cafe Ordering System
# We are building an ordering system for a cafe. Write this in any language using plain classes and objects only. No frameworks, no databases, no APIs.
# The cafe offers:
# Coffees: Espresso, Americano, Latte, Cappuccino, Mocha
# Sizes: Small, Medium, Large
# Optional Toppings: Whipped Cream, Caramel Syrup, Vanilla Syrup, Chocolate Drizzle, Cinnamon
# Requirements:
# - A customer can order multiple drinks
# - Each drink has exactly one coffee type and one size
# - Each drink can have zero or more toppings
# - The system must calculate the total price of the order along with price for each item.
# You decide all prices. State your pricing assumptions before you start.
# Constraints:
# - Plain classes only
# - No databases, no APIs, no frameworks
# - No external libraries
# - Everything runs in memory
# Before writing any code, walk me through your design.
# _


from enum import Enum


class Coffees(Enum):
    Expresso
    Americano
    Latte
    Cappuccino
    Mocha


class Sizes(Enum):
    Small
    Medium
    Large


class Optional_toppings(Enum):
    Whipped_Cream
    Caramel_syrup
    Vanilla_Syrup
    Chocolate_Drizzle
    Cinnamon


class Drink:
    coffees: Coffees
    Sizes: CoffeeSizes
    Optional_toppings: Optional_toppings | None


orders: list[Drink] = []


class OrderCoffe:

    def __init__(self, drink: str, size: str, toppings: str | None = None):
        self.drink = drink,
        self.size = size,
        self.toppings = str

        coffees = Drink(self.drink, self.size, self. toppings)

    def price(coffees: Drink) -> int:

        if (Drink.Coffees == "Expresso") {

        }
        elif (Drink.coffees == "")
