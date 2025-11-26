import sys
import os
import site

# Add venv site-packages to sys.path if running in virtualenv
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    site_packages = os.path.join(sys.prefix, f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
    if os.path.exists(site_packages) and site_packages not in sys.path:
        sys.path.insert(0, site_packages)
        site.addsitedir(site_packages)

import envoxy

# watchdog
try:
    keep_alive = envoxy.Config.get('boot')[0].get('keep_alive', 0)
    envoxy.Watchdog(int(keep_alive)).start()
except (KeyError, TypeError, ValueError, IndexError) as e:
    envoxy.log.system('[{}] watchdog not enabled, keep_alive missing! {}'.format(
        envoxy.log.style.apply('---', envoxy.log.style.YELLOW_FG), e
    ))
