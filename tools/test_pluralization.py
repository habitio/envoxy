"""Test intelligent pluralization for EnvoxyMeta table naming."""
import inflect

inflector = inflect.engine()
examples = [
    "Product", "Person", "Child", "Analysis", "Bus", "Box", "Mouse", "Status", "ClaimHistory", "EntityHistory", "History", "Series", "News", "Data", "Fish", "Sheep"
]

for name in examples:
    # Exceptions for history tables
    if name in {"ClaimHistory", "EntityHistory"} or name.endswith("History"):
        plural = name
    else:
        plural = inflector.plural(name)
    print(f"Class: {name:15} -> Table: aux_{plural.lower()}")
