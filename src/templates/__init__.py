import sys, os
sys.path.append("/home/vorjdux/Projects/muzzley/envoxy/src")
sys.path.append("/home/vorjdux/Projects/muzzley/envoxy/src/templates")

from views.view import HelloWorldView, HelloWorld2View

__loader__ = [HelloWorldView, HelloWorld2View]