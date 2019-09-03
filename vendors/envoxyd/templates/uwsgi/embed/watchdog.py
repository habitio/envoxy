import envoxy

# watchdog
try:
    keep_alive = envoxy.Config.get('boot')[0].get('keep_alive', 0)
    envoxy.Watchdog(int(keep_alive)).start()
except (KeyError, TypeError, ValueError, IndexError) as e:
    envoxy.log.system('[{}] watchdog not enabled, keep_alive missing! {}'.format(
        envoxy.log.style.apply('---', envoxy.log.style.YELLOW_FG), e
    ))
