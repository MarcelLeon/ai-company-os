from aico.app.release_room_demo import run_demo


async def test_release_room_no_token_demo_runs_management_flow() -> None:
    transcript = await run_demo()

    assert "No Telegram bot token or LLM API is required" in transcript
    assert "/team" in transcript
    assert "Team for release-room" in transcript
    assert "Approval required: demo-tas" in transcript
    assert "Task approved: demo-tas" in transcript
    assert "Release plan:" in transcript
    assert "Morning handoff:" in transcript
    assert "Recent audit events:" in transcript
