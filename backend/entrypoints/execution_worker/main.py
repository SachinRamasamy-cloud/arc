"""Independent execution worker deployment entry point."""
from modules.executions.application.worker import process_one
from entrypoints.worker_runtime import resources,run_loop
def main():
    settings,db,store=resources()
    run_loop(lambda: process_one(db,settings,store))

if __name__ == "__main__": main()
