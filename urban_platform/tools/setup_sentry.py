import os

import sentry_sdk


def setup_sentry(dsn: str, environment: str) -> None:
    if environment not in ["production", "staging"]:
        print(f"⚠️ Warning: Sentry is not configured for environment '{environment}'")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=os.environ.get("SENTRY_RELEASE"),
        send_default_pii=True,
        traces_sample_rate=1.0,
    )
