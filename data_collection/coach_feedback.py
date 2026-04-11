"""
Layer 4 — AI Coach Feedback.

Provider is selected via AI_PROVIDER env var:
  groq     → Groq (fast free inference — llama-3.3-70b)
  grok     → xAI Grok
  gemini   → Google Gemini
  claude   → Anthropic Claude
  deepseek → DeepSeek V3
  rule     → rule-based only, no API needed

Set the matching API key env var:
  GROQ_API_KEY
  GROK_API_KEY
  GEMINI_API_KEY   / GOOGLE_API_KEY
  ANTHROPIC_API_KEY
  DEEPSEEK_API_KEY
"""
import os
import json as _json

def _get_config():
    """Read provider config at call time so .env changes are picked up."""
    return {
        "provider":  os.environ.get("AI_PROVIDER", "groq").lower(),
        "groq_key":  os.environ.get("GROQ_API_KEY", ""),
        "grok_key":  os.environ.get("GROK_API_KEY", ""),
        "gemini_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", ""),
        "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "deepseek_key":  os.environ.get("DEEPSEEK_API_KEY", ""),
        "models": {
            "groq":     os.environ.get("GROQ_MODEL",     "llama-3.3-70b-versatile"),
            "grok":     os.environ.get("GROK_MODEL",     "grok-3-mini"),
            "gemini":   os.environ.get("GEMINI_MODEL",   "gemini-2.0-flash-lite"),
            "claude":   os.environ.get("CLAUDE_MODEL",   "claude-3-5-haiku-20241022"),
            "deepseek": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        },
    }

# Keys
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEEPSEEK_API_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")

# Model names — override via env if needed
MODELS = {
    "gemini":   os.environ.get("GEMINI_MODEL",   "gemini-1.5-flash"),
    "claude":   os.environ.get("CLAUDE_MODEL",   "claude-3-5-haiku-20241022"),
    "deepseek": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
}

_client = None

# ── Skill-level detection from verdict history ────────────────────────────────

def _infer_skill_level(history: list | None) -> str:
    if not history or len(history) < 2:
        return "beginner"
    verdicts = [s.get("verdict") for s in history[-5:] if s.get("verdict")]
    elite_count = verdicts.count("ELITE")
    good_count  = verdicts.count("GOOD")
    if elite_count >= 2:   return "advanced"
    if good_count  >= 2:   return "intermediate"
    return "beginner"


# ── Persistent problem detection ──────────────────────────────────────────────

def _find_persistent_problems(report: dict, history: list | None) -> list[str]:
    """Metrics that have been NEEDS IMPROVEMENT for 3+ consecutive sessions."""
    if not history or len(history) < 3:
        return []
    persistent = []
    for metric in report:
        bad_streak = 0
        for session in history[-3:]:
            m = session.get("metrics", {}).get(metric, {})
            if m.get("status") == "NEEDS IMPROVEMENT":
                bad_streak += 1
        if bad_streak == 3:
            persistent.append(metric)
    return persistent


# ── Metric → human explanation mapping ───────────────────────────────────────

METRIC_EXPLANATIONS = {
    # spike
    "arm_cock_angle":  "how far back your hitting arm pulls before contact — the 'bow and arrow' position",
    "jump_height":     "how high you get off the ground at takeoff",
    "approach_speed":  "how fast your 3-step approach is before the jump",
    "contact_point":   "where your hand meets the ball relative to your body — ideally high and in front",
    "follow_through":  "how fully your arm swings through after contact",
    # serve
    "toss_height":     "how high you toss the ball above your contact point",
    "step_timing":     "the rhythm between your step and when you hit",
    "shoulder_rotation": "how much your shoulders rotate through the serve",
    "wrist_snap":      "the snap of your wrist at contact — this generates topspin",
    "body_lean":       "how much your trunk leans forward at contact",
    # block
    "reaction_time":   "how quickly you initiate your jump after reading the attacker",
    "penultimate_step": "the length of your second-to-last step — drives explosive takeoff",
    "hand_position":   "how high your hands get above the net at peak jump",
    "shoulder_width":  "how wide your arms spread at the block — covers more net",
    "landing_balance": "how stable your landing is — critical for injury prevention",
    # dig
    "platform_angle":  "the angle of your forearm platform — controls ball direction",
    "knee_bend":       "how low you get — deeper = more control and power absorption",
    "hip_drop":        "how much you drop your hips to get under the ball",
    "arm_extension":   "how straight your arms are at contact — affects platform consistency",
    "recovery_position": "how quickly you return to ready stance after the dig",
}

METRIC_DRILLS = {
    "arm_cock_angle":  ("Wall shadow drill", "Stand side-on to a wall, practice pulling your elbow back until it touches the wall. 3 sets of 20 reps. Feel: your shoulder blade squeezing toward your spine."),
    "jump_height":     ("Box jump approach", "3-step approach into a box jump, focusing on the penultimate step brake. 4 sets of 6. Feel: your hips loading like a spring on the last step."),
    "approach_speed":  ("Cone approach drill", "Set 3 cones at approach distances, sprint through them. Time yourself. 5 sets. Feel: accelerating INTO the jump, not slowing down."),
    "contact_point":   ("Toss and freeze", "Toss ball to yourself, freeze at contact point with arm fully extended. Check position in mirror. 30 reps. Feel: arm reaching UP and FORWARD, not sideways."),
    "follow_through":  ("Towel swing drill", "Hold a towel, practice full arm swing finishing across your body. 3 sets of 15. Feel: your hand ending near your opposite hip."),
    "toss_height":     ("Toss consistency drill", "Toss ball without hitting, catch it at the same point every time. 50 reps. Feel: the ball hanging at the top of its arc — that's your contact window."),
    "step_timing":     ("Metronome serve", "Use a metronome app at 60bpm, step on beat 1, contact on beat 2. 20 serves. Feel: the rhythm becoming automatic."),
    "shoulder_rotation": ("Resistance band rotation", "Band anchored at shoulder height, rotate through full serve motion. 3x15 each side. Feel: your back shoulder driving forward through contact."),
    "wrist_snap":      ("Wrist snap wall drill", "Stand 1m from wall, snap wrist to hit ball against wall repeatedly. 3x30. Feel: the snap happening AFTER your arm reaches full extension."),
    "body_lean":       ("Lean and freeze", "Practice serve motion, freeze at contact, check lean angle. 20 reps. Feel: your weight transferring forward, not staying back."),
    "reaction_time":   ("Partner signal drill", "Partner points left/right randomly, you shuffle and jump. 4x10. Feel: your feet moving before your brain finishes thinking."),
    "penultimate_step": ("Long-short step drill", "Exaggerate the second-to-last step length. Mark it with tape. 4x8. Feel: that step loading your hips like a coiled spring."),
    "hand_position":   ("Jump and reach drill", "Jump and reach for a target 30cm above net height. 4x8. Feel: your hands penetrating OVER the net, not just reaching the top."),
    "shoulder_width":  ("Wide hands drill", "Practice block jumps with hands as wide as possible. 3x10. Feel: your thumbs pointing forward, not up — covers more net surface."),
    "landing_balance": ("Single-leg landing", "Jump and land on one leg, hold 3 seconds. 3x8 each leg. Feel: your knee tracking over your second toe on landing."),
    "platform_angle":  ("Platform angle mirror drill", "Practice dig position in front of mirror, check forearm angle. 3x20. Feel: your thumbs pointing DOWN, elbows locked straight."),
    "knee_bend":       ("Wall sit progression", "Wall sit at 90°, then 100°, then 110°. Hold 30s each. Feel: your weight in your heels, chest up."),
    "hip_drop":        ("Hip drop to platform", "From standing, drop hips and form platform in one motion. 3x15. Feel: your hips going DOWN before your arms go out."),
    "arm_extension":   ("Locked arm dig", "Partner tosses, you dig with arms locked straight. 3x15. Feel: the ball hitting the flat part of your forearms, not your wrists."),
    "recovery_position": ("Dig and sprint", "Dig a tossed ball, immediately sprint to ready position. 4x10. Feel: your first step out of the dig happening before the ball lands."),
}


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    technique: str,
    report: dict,
    verdict: str,
    skill_level: str,
    persistent_problems: list[str],
    history: list | None,
    peak_frame: int | None,
) -> str:

    # Split metrics into good and bad
    good_metrics = {m: v for m, v in report.items() if v["status"] == "GOOD"}
    bad_metrics  = {m: v for m, v in report.items() if v["status"] == "NEEDS IMPROVEMENT"}

    # Format bad metrics with human explanation
    bad_text = "\n".join(
        f"  - {m} ({METRIC_EXPLANATIONS.get(m, m)}): "
        f"yours={v['value']}, elite avg={v['elite_mean']}"
        + (" [STUCK — 3 sessions in a row]" if m in persistent_problems else "")
        for m, v in bad_metrics.items()
    ) or "  None — all metrics at elite level"

    good_text = "\n".join(
        f"  - {m}: {v['value']} vs elite {v['elite_mean']}"
        for m, v in good_metrics.items()
    ) or "  None yet"

    sessions_text = ""
    if history and len(history) > 1:
        sessions_text = f"\nThis athlete has done {len(history)} sessions. "
        if persistent_problems:
            sessions_text += f"These metrics have NOT improved in 3 sessions: {', '.join(persistent_problems)}. Escalate the drill prescription."

    frame_text = f"\nThe worst biomechanics moment occurs around frame {peak_frame}." if peak_frame else ""

    language_note = {
        "beginner":     "Use simple everyday language. No jargon. Explain what each body part should feel like.",
        "intermediate": "Use coaching language. Reference the movement phases (approach, takeoff, contact, follow-through).",
        "advanced":     "Use biomechanical language. Reference joint angles, force vectors, and timing windows.",
    }[skill_level]

    return f"""You are an Olympic volleyball coach giving feedback after analysing a video.

Technique: {technique.upper()} | Verdict: {verdict} | Athlete level: {skill_level}
{sessions_text}{frame_text}

WHAT NEEDS IMPROVEMENT:
{bad_text}

WHAT IS ALREADY GOOD:
{good_text}

Language style: {language_note}

CRITICAL RULES — you MUST follow these:
- NEVER mention numbers, degrees, angles, or measurements in feel_cue or prescription
- feel_cue must use ONLY body sensation words (e.g. "feel your shoulder blade squeeze", "like drawing a bow", "explosive push from the floor")
- prescription must describe the drill in plain English with sets/reps — no numbers from the analysis
- The athlete cannot measure angles mid-practice — only tell them what to FEEL and DO

Respond in this EXACT JSON structure (no markdown, pure JSON):
{{
  "headline": "One honest sentence about their overall {technique} right now",
  "strengths": ["specific strength 1", "specific strength 2"],
  "fixes": [
    {{
      "metric": "metric_name",
      "problem": "What is actually happening in their body (1 sentence, plain English, no numbers)",
      "feel_cue": "What it should FEEL like when done correctly (sensation words only, no numbers)",
      "drill": "drill name",
      "prescription": "sets/reps and how to do it (no angle numbers)",
      "why_it_works": "1 sentence reason"
    }}
  ],
  "injury_warning": null,
  "next_session_focus": "The ONE thing to focus on next session"
}}

Only include fixes for NEEDS IMPROVEMENT metrics. Max 3 fixes."""


# ── Main function ─────────────────────────────────────────────────────────────

def generate_feedback(
    technique: str,
    report: dict,
    verdict: str,
    history: list | None = None,
    peak_frame: int | None = None,
) -> dict:
    cfg         = _get_config()
    provider    = cfg["provider"]
    rule_based  = _rule_based_feedback(technique, report)
    skill_level = _infer_skill_level(history)
    persistent  = _find_persistent_problems(report, history)
    prompt      = _build_prompt(technique, report, verdict, skill_level, persistent, history, peak_frame)

    if provider == "rule":
        return rule_based

    try:
        raw    = _call_provider(prompt, cfg)
        raw    = _strip_fences(raw)
        parsed = _json.loads(raw)
        parsed["skill_level"]       = skill_level
        parsed["provider"]          = provider
        parsed["model"]             = cfg["models"].get(provider, provider)
        parsed["rule_based_drills"] = rule_based["fixes"]
        return parsed
    except Exception as e:
        rule_based["error"]    = str(e)
        rule_based["provider"] = provider
        return rule_based


def _call_provider(prompt: str, cfg: dict) -> str:
    provider = cfg["provider"]
    if provider == "groq":
        return _call_groq(prompt, cfg)
    if provider == "grok":
        return _call_grok(prompt, cfg)
    if provider == "gemini":
        return _call_gemini(prompt, cfg)
    if provider == "claude":
        return _call_claude(prompt, cfg)
    if provider == "deepseek":
        return _call_deepseek(prompt, cfg)
    raise ValueError(f"Unknown AI_PROVIDER: '{provider}'")


def _call_groq(prompt: str, cfg: dict) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg["groq_key"], base_url="https://api.groq.com/openai/v1")
    resp = client.chat.completions.create(
        model=cfg["models"]["groq"],
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return resp.choices[0].message.content


def _call_grok(prompt: str, cfg: dict) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg["grok_key"], base_url="https://api.x.ai/v1")
    resp = client.chat.completions.create(
        model=cfg["models"]["grok"],
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def _call_gemini(prompt: str, cfg: dict) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=cfg["gemini_key"])
    response = client.models.generate_content(
        model=cfg["models"]["gemini"],
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return response.text


def _call_claude(prompt: str, cfg: dict) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=cfg["anthropic_key"])
    msg = client.messages.create(
        model=cfg["models"]["claude"],
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _call_deepseek(prompt: str, cfg: dict) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg["deepseek_key"], base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=cfg["models"]["deepseek"],
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _rule_based_feedback(technique: str, report: dict) -> dict:
    """
    Fallback: pure rule-based feedback using the drill library.
    Works without Claude API. Always included as backup.
    """
    bad_metrics = {m: v for m, v in report.items() if v["status"] == "NEEDS IMPROVEMENT"}
    good_metrics = {m: v for m, v in report.items() if v["status"] == "GOOD"}

    fixes = []
    for metric, val in list(bad_metrics.items())[:3]:
        drill_name, prescription = METRIC_DRILLS.get(metric, ("Focused practice", f"Work specifically on {metric}. Consult your coach."))
        gap = round(val["value"] - val["elite_mean"], 2)
        fixes.append({
            "metric":       metric,
            "problem":      f"{METRIC_EXPLANATIONS.get(metric, metric)} is {abs(gap):.1f} units {'below' if gap < 0 else 'above'} elite average",
            "feel_cue":     METRIC_DRILLS.get(metric, ("", ""))[1].split("Feel: ")[-1] if "Feel: " in METRIC_DRILLS.get(metric, ("", ""))[1] else "",
            "drill":        drill_name,
            "prescription": prescription,
            "why_it_works": "Isolates the specific movement pattern that needs reinforcement",
        })

    return {
        "headline": f"{'All metrics at elite level' if not bad_metrics else f'{len(bad_metrics)} metric(s) need work'} on your {technique}.",
        "strengths": [f"{m}: {v['value']} (elite: {v['elite_mean']})" for m, v in list(good_metrics.items())[:2]],
        "fixes": fixes,
        "injury_warning": None,
        "next_session_focus": fixes[0]["metric"] if fixes else "Maintain current form",
        "skill_level": "unknown",
        "model": "rule_based",
    }
