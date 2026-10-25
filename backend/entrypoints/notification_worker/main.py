"""Independent notification worker deployment entry point."""
from modules.notifications.application.deliveries import deliver_mail,reminders
from entrypoints.worker_runtime import resources,run_loop
def main():
    settings,db,_=resources()
    def work():
        deliver_mail(db,settings)
        reminders(db,settings)
        return False
    run_loop(work,periodic_seconds=30)

if __name__ == "__main__": main()
