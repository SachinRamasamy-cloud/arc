"""Independent webhook worker deployment entry point."""
from modules.notifications.application.deliveries import deliver_webhook
from entrypoints.worker_runtime import resources,run_loop
def main():
    settings,db,_=resources()
    run_loop(lambda: deliver_webhook(db,settings))

if __name__ == "__main__": main()
