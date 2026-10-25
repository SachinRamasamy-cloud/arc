"""One-shot verified accounting review; automatic refunds/grants are never inferred."""
import argparse,json
from foundation.config.settings import Settings
from foundation.database.session import Database
from modules.payments.application.reconciliation import accounting_report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',required=True)
    args=parser.parse_args()
    settings=Settings();database=Database(settings.database_url)
    with database.session() as db:
        print(json.dumps(accounting_report(db,args.workspace),indent=2))
if __name__ == '__main__': main()
