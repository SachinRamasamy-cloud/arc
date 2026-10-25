"""Independent scheduler deployment entry point."""
from modules.executions.application.worker import recover_expired
from modules.metering.application.accounting import meter_storage_batch
from entrypoints.worker_runtime import resources,run_loop
def main():
    settings,db,_=resources()
    def work():
        meter_storage_batch(db,settings)
        recover_expired(db,settings)
        return False
    run_loop(work,periodic_seconds=60)

if __name__ == "__main__": main()
