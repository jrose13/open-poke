from composio import Composio


def get_stripe_tools(composio_client: Composio, user_id: str):
    return composio_client.tools.get(
        user_id,
        toolkits=[
            "STRIPE",
        ],
    )


def get_google_tools(composio_client: Composio, user_id: str):
    return composio_client.tools.get(
        user_id,
        tools=[
            "GMAIL_SEARCH_PEOPLE",
            "GMAIL_GET_PROFILE",
            "GMAIL_SEND_EMAIL",
            "GMAIL_GET_EMAIL_THREAD",
            "GMAIL_CREATE_EMAIL_DRAFT",
            "COMPOSIO_SEARCH_SEARCH",
            "COMPOSIO_SEARCH_EXA_SIMILARLINK",
            "COMPOSIO_SEARCH_EXA_ANSWER",
        ],
    )


def get_voyager_tools(composio_client: Composio, user_id: str):
    """Placeholder Voyager tool loader (extend as integrations come online)."""
    try:
        return composio_client.tools.get(user_id, tools=[])
    except Exception as exc:  # pragma: no cover - defensive logging path
        print(f"[Voyager Debug] get_voyager_tools fallback: {exc}")
        return []
