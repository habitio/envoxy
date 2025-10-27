import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../src/envoxy'))

try:
    # import envoxy
    sys.stdout.write('Envoxy Python Interactive Shell Loaded\n')
    sys.stdout.flush()
except Exception as e:
    sys.stdout.write('Error to import Envoxy!\n')
    sys.stdout.write(str(e))
    sys.stdout.flush()
    exit(-10)