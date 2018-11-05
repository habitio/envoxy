import sys
import uwsgi

print('\n\n')
print('======================================')
print('=== ENVOXY Bootstrap System Loader ===')
print('======================================')
print('\n\n')
print(">>> I am the bootstrap for uwsgi.SymbolsImporter")
print('\n\n')

sys.meta_path.insert(0, uwsgi.SymbolsImporter())