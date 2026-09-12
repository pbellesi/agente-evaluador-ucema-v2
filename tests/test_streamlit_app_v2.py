from pathlib import Path
import app_v2


def test_public_streamlit_constants_pinned_to_gemini():
    assert app_v2.OFFICIAL_PROVIDER == "Gemini"
    assert app_v2.OFFICIAL_MODEL == "gemini-3.5-flash-lite"


def test_public_streamlit_no_nvidia_or_deepseek_in_ui():
    app_source = Path(app_v2.__file__).read_text(encoding="utf-8")
    assert "nvidia" not in app_source.lower(), "app_v2.py should not reference nvidia in the public UI"
    assert "deepseek" not in app_source.lower(), "app_v2.py should not reference deepseek in the public UI"
    assert "LLM_PROVIDER" not in app_source, "app_v2.py should not use LLM_PROVIDER selector"
    assert "NVIDIA_API_KEY" not in app_source, "app_v2.py should not reference NVIDIA_API_KEY"


def test_public_streamlit_evaluator_pinned():
    app_source = Path(app_v2.__file__).read_text(encoding="utf-8")
    assert "evaluate_simple_zip" in app_source
    assert "GEMINI_API_KEY" in app_source
