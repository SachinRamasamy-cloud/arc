"""Independent retention worker deployment entry point."""
from modules.notifications.application.deliveries import cleanup_expired
from entrypoints.worker_runtime import resources,run_loop
def main():
    settings,db,store=resources()
    run_loop(lambda: cleanup_expired(db,settings,store),periodic_seconds=60)

if __name__ == "__main__": main()
