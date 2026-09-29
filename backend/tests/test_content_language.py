"""English (Latin-script) content support: language detection, prompt selection, and the
language-dependent bits of steps 1–5 and export. No model calls."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.core.shared_config import PROMPT_DIR, PROMPT_FILES, get_prompt_files
from backend.pipeline import language as lang
from backend.pipeline.quality import profile_for, to_srt_time

CATEGORIES = ["default", "business", "content_review", "entertainment", "experience",
              "knowledge", "opinion", "speech"]
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")

EN_TEXT = ("Welcome back to the show. Today we have a founder who built a battery startup, "
           "and we're going to talk about fundraising mistakes and advice for new founders.")
ZH_TEXT = "欢迎回到节目，今天我们请到了一位做电池创业的创始人，聊聊融资踩过的坑和给新创业者的建议。"


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv(lang.ENV_OVERRIDE, raising=False)


def _cues(texts, step=6.0):
    return [{"index": i + 1, "start_time": to_srt_time(i * step), "end_time": to_srt_time(i * step + step - 0.4),
             "text": t} for i, t in enumerate(texts)]


def _write_chunks(metadata_dir: Path, texts):
    d = metadata_dir / "step1_srt_chunks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "chunk_0.json").write_text(json.dumps(_cues(texts), ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ detection ---
@pytest.mark.parametrize("text,expected", [
    (EN_TEXT, "en"),
    (ZH_TEXT, "zh"),
    ("我们用AI做了一个ChatGPT的demo，然后用Python和React把它部署到了AWS上，效果还不错。", "zh"),
    ("今日はAIについて話しましょう。とても面白いテーマです。", "zh"),
    ("오늘은 인공지능에 대해 이야기해 봅시다. 아주 재미있는 주제입니다.", "zh"),
    ("Hoy vamos a hablar de los errores más comunes al buscar financiación para una startup.", "en"),
    ("Сегодня мы поговорим о типичных ошибках при поиске финансирования.", "zh"),
    ("OK yes", "zh"),  # too little text to decide: keep the original behaviour
    ("", "zh"),
])
def test_detect_language(text, expected):
    assert lang.detect_language(text) == expected


def test_english_transcript_with_a_few_chinese_names_is_still_english():
    text = " ".join([EN_TEXT] * 5) + " 张三 李四"
    assert lang.detect_language(text) == "en"


def test_env_override_wins_and_bad_value_falls_back_to_auto(monkeypatch, tmp_path):
    monkeypatch.setenv(lang.ENV_OVERRIDE, "en")
    assert lang.decide_language(_cues([ZH_TEXT]))["language"] == "en"
    assert lang.load_language(tmp_path) == "en"
    monkeypatch.setenv(lang.ENV_OVERRIDE, "zh")
    assert lang.decide_language(_cues([EN_TEXT]))["language"] == "zh"
    monkeypatch.setenv(lang.ENV_OVERRIDE, "klingon")
    assert lang.decide_language(_cues([EN_TEXT]))["language"] == "en"
    monkeypatch.setenv(lang.ENV_OVERRIDE, "AUTO")
    assert lang.decide_language(_cues([ZH_TEXT]))["language"] == "zh"


def test_load_language_reads_file_then_redetects_then_defaults(tmp_path):
    assert lang.load_language(None) == "zh"
    assert lang.load_language(tmp_path) == "zh"  # nothing saved, no chunks
    _write_chunks(tmp_path, [EN_TEXT])
    assert lang.load_language(tmp_path) == "en"  # re-detected from step1 chunks
    lang.save_language({"language": "zh", "source": "auto"}, tmp_path)
    assert lang.load_language(tmp_path) == "zh"  # the saved decision wins
    (tmp_path / lang.LANGUAGE_FILE).write_text("{not json", encoding="utf-8")
    assert lang.load_language(tmp_path) == "en"  # corrupt file: fall back to re-detection


def test_language_of_payload_ignores_ascii_keys():
    assert lang.language_of_payload([{"title": "融资踩过的坑", "content": ["估值谈判", "尽调"]}]) == "zh"
    assert lang.language_of_payload([{"title": "Fundraising mistakes", "content": ["Pick the right investors early"]}]) == "en"


def test_transcription_language():
    assert lang.transcription_language("auto") == "auto"
    assert lang.transcription_language(None) == "auto"
    assert lang.transcription_language("ja") == "ja"


def test_transcription_language_uses_override_only_when_auto(monkeypatch):
    monkeypatch.setenv(lang.ENV_OVERRIDE, "en")
    assert lang.transcription_language("auto") == "en"
    assert lang.transcription_language("zh") == "zh"  # an explicit setting is never replaced


# ------------------------------------------------------------------ prompt files ---
def test_zh_paths_are_never_changed():
    for cat in CATEGORIES:
        for path in get_prompt_files(cat).values():
            assert lang.localize_prompt_path(path, "zh") == Path(path)


def test_every_bundled_prompt_has_an_english_twin_without_cjk():
    for cat in CATEGORIES:
        for key, path in get_prompt_files(cat).items():
            en = lang.localize_prompt_path(path, "en")
            assert en != Path(path), (cat, key)
            assert en.exists(), (cat, key)
            assert (PROMPT_DIR / "en") in en.parents
            assert not CJK.search(en.read_text(encoding="utf-8")), en


def test_category_prompt_maps_to_same_category(tmp_path):
    en = lang.localize_prompt_path(PROMPT_DIR / "business" / "推荐理由.txt", "en")
    assert en == PROMPT_DIR / "en" / "business" / "scoring.txt"
    # knowledge has no own scoring prompt in Chinese either: falls back to the English default
    en = lang.localize_prompt_path(PROMPT_DIR / "knowledge" / "推荐理由.txt", "en")
    assert en == PROMPT_DIR / "en" / "scoring.txt"


def test_custom_prompt_outside_prompt_dir_is_kept(tmp_path):
    custom = tmp_path / "大纲.txt"
    custom.write_text("my prompt", encoding="utf-8")
    assert lang.localize_prompt_path(custom, "en") == custom


def test_english_prompts_keep_the_output_contract_the_code_parses():
    """Output formats must match the parsers in steps 1–5 (same contract as the default Chinese prompts)."""
    for cat in CATEGORIES:
        files = {k: lang.localize_prompt_path(v, "en").read_text(encoding="utf-8") for k, v in get_prompt_files(cat).items()}
        assert "### Outline:" in files["outline"] and "1.  **" in files["outline"], cat
        assert "`outline`" in files["timeline"] and "start_time" in files["timeline"], cat
        assert "final_score" in files["recommendation"] and "recommend_reason" in files["recommendation"], cat
        assert '"1":' in files["title"], cat
        for field in ("collection_title", "collection_summary", "clips"):
            assert field in files["clustering"], (cat, field)
        assert "generated_title" in files["collection_title"], cat


def test_english_outline_example_parses(tmp_path):
    from backend.pipeline.step1_outline import OutlineExtractor
    ex = OutlineExtractor(metadata_dir=tmp_path)
    ex.language = "en"
    for cat in CATEGORIES:
        text = lang.localize_prompt_path(get_prompt_files(cat)["outline"], "en").read_text(encoding="utf-8")
        example = text.split("## Output example", 1)[1].split("\n## ", 1)[0]
        topics = ex._parse_outline_response(example, 0)
        assert len(topics) >= 2, cat
        assert all(t["title"] and "*" not in t["title"] for t in topics), cat
        assert all(len(t["subtopics"]) >= 2 for t in topics), cat


# ------------------------------------------------------------------ steps ---
def test_step1_writes_language_and_uses_english_prompt(tmp_path, monkeypatch):
    from backend.pipeline import step1_outline
    srt = tmp_path / "talk.srt"
    srt.write_text("\n".join(f"{c['index']}\n{c['start_time']} --> {c['end_time']}\n{c['text']}\n"
                             for c in _cues([EN_TEXT] * 20)), encoding="utf-8")
    seen = {}

    def fake_call(self, prompt, input_data=None, max_retries=3):
        seen["prompt"] = prompt
        return "### Outline:\n1.  **Fundraising mistakes** (about 2 minutes)\n    - Picking the wrong investors\n"

    monkeypatch.setattr(step1_outline.LLMClient, "call_with_retry", fake_call)
    outlines = step1_outline.OutlineExtractor(metadata_dir=tmp_path).extract_outline(srt)
    assert outlines[0]["title"] == "Fundraising mistakes"
    assert json.loads((tmp_path / lang.LANGUAGE_FILE).read_text())["language"] == "en"
    assert "You are a professional video content structure analyst" in seen["prompt"]
    assert "Parameters for this task" in seen["prompt"] and "本次任务参数" not in seen["prompt"]


def test_step1_chinese_prompt_is_byte_identical_to_before(tmp_path, monkeypatch):
    from backend.pipeline import step1_outline
    srt = tmp_path / "talk.srt"
    srt.write_text("\n".join(f"{c['index']}\n{c['start_time']} --> {c['end_time']}\n{c['text']}\n"
                             for c in _cues([ZH_TEXT] * 20)), encoding="utf-8")
    seen = {}

    def fake_call(self, prompt, input_data=None, max_retries=3):
        seen["prompt"] = prompt
        return "### 大纲：\n1.  **融资踩坑**（预计2分钟）\n    - 选错投资人\n"

    monkeypatch.setattr(step1_outline.LLMClient, "call_with_retry", fake_call)
    step1_outline.OutlineExtractor(metadata_dir=tmp_path).extract_outline(srt)
    profile = profile_for(20 * 6 - 0.4)
    expected = Path(PROMPT_FILES["outline"]).read_text(encoding="utf-8") + profile.prompt_hint()
    assert seen["prompt"] == expected
    assert json.loads((tmp_path / lang.LANGUAGE_FILE).read_text())["language"] == "zh"


@pytest.mark.parametrize("language", ["zh", "en"])
def test_steps_2_to_5_load_the_matching_prompt(tmp_path, language):
    from backend.pipeline.step2_timeline import TimelineExtractor
    from backend.pipeline.step3_scoring import ClipScorer
    from backend.pipeline.step4_title import TitleGenerator
    from backend.pipeline.step5_clustering import ClusteringEngine

    lang.save_language({"language": language, "source": "test"}, tmp_path)
    for cat in CATEGORIES:
        pf = get_prompt_files(cat)
        pairs = [
            (TimelineExtractor(metadata_dir=tmp_path, prompt_files=pf).timeline_prompt, pf["timeline"]),
            (ClipScorer(prompt_files=pf, metadata_dir=tmp_path).recommendation_prompt, pf["recommendation"]),
            (TitleGenerator(metadata_dir=tmp_path, prompt_files=pf).title_prompt, pf["title"]),
            (ClusteringEngine(metadata_dir=tmp_path, prompt_files=pf).clustering_prompt, pf["clustering"]),
        ]
        for loaded, zh_path in pairs:
            expected = lang.localize_prompt_path(zh_path, language).read_text(encoding="utf-8")
            assert loaded == expected, (cat, zh_path)
            if language == "zh":
                assert loaded == Path(zh_path).read_text(encoding="utf-8")


def test_step3_excerpt_length_scales_with_language(tmp_path):
    from backend.pipeline.step3_scoring import ClipScorer
    long_text = "word " * 2000
    _write_chunks(tmp_path, [long_text])
    lang.save_language({"language": "en"}, tmp_path)
    clip = {"start_time": "00:00:00,000", "end_time": "00:00:05,000"}
    assert len(ClipScorer(metadata_dir=tmp_path)._excerpt(clip)) == 2400
    lang.save_language({"language": "zh"}, tmp_path)
    assert len(ClipScorer(metadata_dir=tmp_path)._excerpt(clip)) == 600


def test_step5_english_labels_and_fallback(tmp_path, monkeypatch):
    from backend.pipeline import step5_clustering
    lang.save_language({"language": "en"}, tmp_path)
    engine = step5_clustering.ClusteringEngine(metadata_dir=tmp_path)
    clips = [
        {"id": "1", "outline": "a", "generated_title": "Why startups fail at fundraising", "recommend_reason": "Founders and investors", "final_score": 0.9},
        {"id": "2", "outline": "b", "generated_title": "How to pitch investors", "recommend_reason": "Startup funding advice", "final_score": 0.8},
        {"id": "3", "outline": "c", "generated_title": "Sleep and exercise habits", "recommend_reason": "Health tips", "final_score": 0.7},
    ]
    seen = {}

    def fake_call(self, prompt, input_data=None, max_retries=3):
        seen["prompt"] = prompt
        raise RuntimeError("model down")

    monkeypatch.setattr(step5_clustering.LLMClient, "call_with_retry", fake_call)
    collections = engine.cluster_clips(clips)
    assert "Here is the list of video clips:" in seen["prompt"]
    assert "Title: Why startups fail at fundraising" in seen["prompt"]
    assert not CJK.search(seen["prompt"])
    assert collections and collections[0]["collection_title"] == "Business & startups"
    assert collections[0]["clip_ids"] == ["1", "2"]
    # word matching, not substring: "ai" must not match "said" / "again"
    assert engine._pre_cluster_by_keywords_en([
        {"id": "1", "title": "He said it again", "summary": ""},
        {"id": "2", "title": "Again, she said", "summary": ""},
    ]) == {}


def test_step5_chinese_prompt_unchanged(tmp_path, monkeypatch):
    from backend.pipeline import step5_clustering
    lang.save_language({"language": "zh"}, tmp_path)
    engine = step5_clustering.ClusteringEngine(metadata_dir=tmp_path)
    seen = {}

    def fake_call(self, prompt, input_data=None, max_retries=3):
        seen["prompt"] = prompt
        return "[]"

    monkeypatch.setattr(step5_clustering.LLMClient, "call_with_retry", fake_call)
    engine.cluster_clips([{"id": "1", "outline": "投资", "generated_title": "股票投资", "recommend_reason": "理财", "final_score": 0.9}])
    assert seen["prompt"].startswith(Path(PROMPT_FILES["clustering"]).read_text(encoding="utf-8") + "\n\n以下是视频切片列表：\n")
    assert "1. 标题：股票投资\n   摘要：理财\n   评分：0.90" in seen["prompt"]


def test_english_duration_hint_has_same_numbers():
    for total in (300, 1200, 5400):
        p = profile_for(total)
        en = p.prompt_hint("en")
        assert "Parameters for this task" in en and not CJK.search(en)
        assert f"{p.topics_hint[0]}–{p.topics_hint[1]} topics" in en


# ------------------------------------------------------------------ export ---
def test_title_card_text():
    from backend.services.publish_export import title_card_text
    zh = "科技股现在能买吗？AI算力基建是关键，这类公司值得关注这类公司值得关注这类公司值得关注"
    assert title_card_text(zh) == zh[:40]
    assert title_card_text("Short title") == "Short title"
    card = title_card_text("Is it time to buy tech stocks? Why AI infrastructure companies deserve a look right now")
    lines = card.split("\n")
    assert len(lines) == 2 and all(len(line) <= 36 for line in lines)
    assert lines[1].endswith("…")
    assert all(w in "Is it time to buy tech stocks? Why AI infrastructure companies deserve a look right now"
               for w in " ".join(lines).rstrip("…").split())


def test_cover_split_title_keeps_words_whole():
    from backend.services.cover import split_title
    assert split_title("为什么大厂都在裁员，普通人该怎么办？") == ["为什么大厂都在裁员", "普通人该怎么办？"]
    lines = split_title("The real reason: Why battery storage is the bottleneck")
    assert lines == ["The real reason: Why battery", "storage is the bottleneck"]


def test_english_scoring_prompts_ask_for_short_complete_replies():
    """Echoing every input field back (incl. the transcript) made Gemini drop the scores: ask for 3 fields only."""
    import json as _json
    for cat in CATEGORIES:
        text = lang.localize_prompt_path(get_prompt_files(cat)["recommendation"], "en").read_text(encoding="utf-8")
        section = text.split("## Output format", 1)[1]
        assert "Do **not** repeat" in section and "transcript" in section, cat
        example = section.split("```json", 1)[1].split("```", 1)[0]
        for item in _json.loads(example):
            assert set(item) == {"outline", "final_score", "recommend_reason"}, cat
