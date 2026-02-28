from pathlib import Path


def suggest(text: str, ctx: list[dict]) -> list[str]:
    q = text.lower()
    points = []
    if ctx:
        points.append(f"Reference: {Path(ctx[0]['path']).name} (score {ctx[0]['score']:.2f})")
    if any(k in q for k in ["pricing", "cost", "budget"]):
        points.append("Ask budget + timeline before offering scope.")
    if any(k in q for k in ["next", "plan", "roadmap"]):
        points.append("Propose 2 concrete next actions with owners/dates.")
    if any(k in q for k in ["issue", "problem", "blocked"]):
        points.append("Restate the issue in one line, then suggest a testable fix.")
    if not points:
        points.append("Structure: clarify goal → constraints → one concrete move.")
    return points[:3]
