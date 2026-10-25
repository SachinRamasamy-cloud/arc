"""Inspect queued development mail without requiring an SMTP service."""
import argparse

from sqlalchemy import select

from foundation.config.settings import Settings
from foundation.crypto.security import unseal
from foundation.database.session import Database
from modules.notifications.public import Mail


def main(argv=None, *, settings=None):
    parser = argparse.ArgumentParser(description="Arc customer identity development tools")
    parser.add_argument("command", choices=["mail"])
    parser.add_argument("--email", required=True, help="Recipient whose latest queued messages to display")
    args = parser.parse_args(argv)
    settings = settings or Settings()
    if settings.env not in {"development", "test"}:
        raise SystemExit("The local mailbox is available only in development or test.")
    database = Database(settings.database_url)
    try:
        with database.session() as session:
            messages = session.scalars(select(Mail).where(Mail.recipient == args.email.lower()).order_by(Mail.created_at.desc(), Mail.id.desc()).limit(20))
            count = 0
            for message in messages:
                print(message.recipient, message.subject, unseal(message.body_encrypted, settings, "mail"), sep="\n")
                print()
                count += 1
            if not count:
                print("No queued messages for this recipient.")
    finally:
        database.engine.dispose()


if __name__ == "__main__":
    main()
