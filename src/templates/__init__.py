import sys, os
sys.path.append("/home/vorjdux/Projects/muzzley/envoxy/src")
sys.path.append("/home/vorjdux/Projects/muzzley/envoxy/src/templates")

from views.view import HelloWorldCollection, HelloWorldDocument

__loader__ = [HelloWorldCollection, HelloWorldDocument]