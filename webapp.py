"""Minimal local web UI for shortstoryfun (127.0.0.1 only).

CLI remains the primary interface. This UI is a thin convenience layer
over the same Markdown story folders and checkpoints.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

from src.shortstory.cost import CostTracker
from src.shortstory.pipeline import (
    CheckpointError,
    approve_outline,
    approve_premise,
    assemble_draft,
    continuity_check,
    create_spark,
    draft_scenes,
    generate_outline,
    generate_premises,
    list_frameworks,
    redraft_scene,
)
from src.shortstory.pipeline.engine import make_engine
from src.shortstory.providers import create_provider, get_draft_model_name, get_premium_model_name
from src.shortstory.storage import (
    DEFAULT_STORIES_ROOT,
    list_stories,
    read_meta,
    read_text,
    require_story,
)
from src.shortstory.style import check_ip_safety

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent
MONTHLY_TOTALS = REPO_ROOT / "data" / "monthly_costs.jsonl"

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>shortstoryfun (local)</title>
  <style>
    :root { --ink:#1a1a1a; --paper:#f7f4ef; --accent:#2f5d50; --warn:#8a4b2e; }
    body { font-family: "Iowan Old Style", "Palatino Linotype", Palatino, serif;
           margin:0; background:linear-gradient(160deg,#f7f4ef,#e8efe9 50%,#f3eee6);
           color:var(--ink); min-height:100vh; }
    main { max-width:720px; margin:0 auto; padding:2.5rem 1.25rem 4rem; }
    h1 { font-size:2.4rem; letter-spacing:-0.02em; margin:0 0 .25rem; }
    .tag { color:var(--warn); font-size:.95rem; margin-bottom:1.5rem; }
    label { display:block; font-size:.9rem; margin:.8rem 0 .3rem; }
    textarea, input, select { width:100%; box-sizing:border-box; padding:.65rem .7rem;
      border:1px solid #c9c2b6; border-radius:4px; background:#fffdf8; font:inherit; }
    textarea { min-height:120px; }
    .row { display:flex; gap:.6rem; flex-wrap:wrap; margin-top:1rem; }
    button { background:var(--accent); color:#fff; border:0; padding:.65rem 1rem;
      border-radius:4px; cursor:pointer; font:inherit; }
    button.secondary { background:#4a4a4a; }
    pre { background:#1e1e1e; color:#e8e8e8; padding:1rem; overflow:auto;
      border-radius:4px; white-space:pre-wrap; }
    .stories a { color:var(--accent); margin-right:.8rem; }
  </style>
</head>
<body>
<main>
  <h1>shortstoryfun</h1>
  <p class="tag">Private local drafting · output is always a raw draft for you to rewrite</p>

  <section>
    <h2>New spark</h2>
    <label for="spark">Your raw idea</label>
    <textarea id="spark" placeholder="A night clerk in Flagstaff finds a ledger that rewrites itself…"></textarea>
    <label for="slug">Slug (optional)</label>
    <input id="slug" placeholder="flagstaff-ledger"/>
    <div class="row">
      <button onclick="api('spark')">Save spark</button>
    </div>
  </section>

  <section>
    <h2>Continue a story</h2>
    <label for="story">Slug</label>
    <input id="story" list="storylist"/>
    <datalist id="storylist">
      {% for s in stories %}<option value="{{ s }}">{% endfor %}
    </datalist>
    <label for="framework">Framework</label>
    <select id="framework">
      {% for key in frameworks %}<option value="{{ key }}">{{ key }}</option>{% endfor %}
    </select>
    <label><input type="checkbox" id="premium"/> Use premium model (manual only)</label>
    <div class="row">
      <button onclick="api('premise')">Premise ×3</button>
      <button class="secondary" onclick="api('approve-premise')">Approve premise</button>
      <button onclick="api('outline')">Outline</button>
      <button class="secondary" onclick="api('approve-outline')">Approve outline</button>
      <button onclick="api('draft')">Draft scenes</button>
      <button onclick="api('assemble')">Assemble</button>
      <button class="secondary" onclick="api('cost')">Cost report</button>
    </div>
  </section>

  <section>
    <h2>Output</h2>
    <pre id="out">Ready.</pre>
  </section>
</main>
<script>
async function api(action) {
  const out = document.getElementById('out');
  out.textContent = 'Working…';
  const body = {
    action,
    spark: document.getElementById('spark').value,
    slug: document.getElementById('slug').value || document.getElementById('story').value,
    story: document.getElementById('story').value,
    framework: document.getElementById('framework').value,
    premium: document.getElementById('premium').checked,
  };
  const res = await fetch('/api/action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  const data = await res.json();
  out.textContent = data.ok ? (data.message || JSON.stringify(data, null, 2))
                            : ('Error: ' + (data.error || res.status));
  if (data.slug) document.getElementById('story').value = data.slug;
}
</script>
</body>
</html>
"""


def create_app() -> Flask:
    """Create the minimal local Flask app."""
    app = Flask(__name__)

    def _provider(premium: bool):
        model = get_premium_model_name() if premium else get_draft_model_name()
        return create_provider(model_name=model)

    def _engine(slug: str, premium: bool = False):
        paths = require_story(slug)
        return make_engine(
            paths,
            _provider(premium),
            monthly_totals_path=MONTHLY_TOTALS,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )

    @app.get("/")
    def index():
        return render_template_string(
            PAGE,
            stories=list_stories(),
            frameworks=sorted(list_frameworks().keys()),
        )

    @app.get("/api/stories")
    def api_stories():
        items = []
        for slug in list_stories():
            paths = require_story(slug)
            items.append({"slug": slug, "meta": read_meta(paths)})
        return jsonify(items)

    @app.post("/api/action")
    def api_action():
        data = request.get_json(force=True, silent=True) or {}
        action = (data.get("action") or "").strip()
        premium = bool(data.get("premium"))
        try:
            if action == "spark":
                spark = (data.get("spark") or "").strip()
                gate = check_ip_safety(spark)
                if not gate.ok:
                    return jsonify({"ok": False, "error": gate.explanation}), 400
                slug = (data.get("slug") or None) or None
                paths = create_spark(spark, slug=slug if slug else None)
                return jsonify({"ok": True, "slug": paths.root.name, "message": f"Created {paths.root}"})

            slug = (data.get("story") or data.get("slug") or "").strip()
            if not slug:
                return jsonify({"ok": False, "error": "story slug required"}), 400

            if action == "approve-premise":
                approve_premise(require_story(slug))
                return jsonify({"ok": True, "slug": slug, "message": "Premise approved"})
            if action == "approve-outline":
                approve_outline(require_story(slug))
                return jsonify({"ok": True, "slug": slug, "message": "Outline approved"})
            if action == "assemble":
                assemble_draft(require_story(slug))
                paths = require_story(slug)
                return jsonify({"ok": True, "slug": slug, "message": read_text(paths.draft)[:4000]})
            if action == "cost":
                paths = require_story(slug)
                report = CostTracker(paths.costs, monthly_totals_path=MONTHLY_TOTALS).format_report()
                return jsonify({"ok": True, "slug": slug, "message": report})

            engine = _engine(slug, premium=premium)
            if action == "premise":
                generate_premises(engine)
                msg = read_text(engine.paths.premise) + "\n\n" + engine.costs.format_report()
                return jsonify({"ok": True, "slug": slug, "message": msg})
            if action == "outline":
                framework = data.get("framework") or "story_circle"
                generate_outline(engine, framework=framework, target_words=int(data.get("words") or 5000))
                msg = read_text(engine.paths.outline) + "\n\n" + engine.costs.format_report()
                return jsonify({"ok": True, "slug": slug, "message": msg})
            if action == "draft":
                written = draft_scenes(engine)
                msg = "Wrote:\n" + "\n".join(str(p) for p in written) + "\n\n" + engine.costs.format_report()
                return jsonify({"ok": True, "slug": slug, "message": msg})
            if action == "redraft":
                scene = int(data.get("scene") or 1)
                path = redraft_scene(engine, scene)
                return jsonify({"ok": True, "slug": slug, "message": f"Rewrote {path}"})
            if action == "continuity":
                continuity_check(engine)
                return jsonify({"ok": True, "slug": slug, "message": read_text(engine.paths.continuity)})

            return jsonify({"ok": False, "error": f"Unknown action: {action}"}), 400
        except CheckpointError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "stories_root": str(DEFAULT_STORIES_ROOT)})

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=os.getenv("FLASK_ENV") == "development")
