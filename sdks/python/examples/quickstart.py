"""CozyMemory Python SDK quickstart.

Run after you have a CozyMemory server + a dashboard-issued API key.
"""
from cozymemory import CozyMemoryClient


def main() -> None:
    with CozyMemoryClient(
        api_key="cozy_live_<your-key>",
        base_url="http://localhost:8000",
    ) as c:
        # Write a memory
        c.conversations.add(
            user_id="alice",
            messages=[
                {"role": "user", "content": "I love hiking"},
                {"role": "assistant", "content": "Got it, I'll remember."},
            ],
        )
        # Fetch unified context for LLM prompt
        ctx = c.context.get_unified(user_id="alice", query="outdoor activity")
        print("Conversations:", len(ctx.get("conversations", [])))
        print("Profile:", ctx.get("profile_context"))
        print("Knowledge:", ctx.get("knowledge"))


if __name__ == "__main__":
    main()
