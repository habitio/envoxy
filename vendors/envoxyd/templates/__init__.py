import sys
import os
sys.path.append("${app_path}")

from views.view import CardsCollection, CardsDocument

__loader__ = [CardsCollection, CardsDocument]
