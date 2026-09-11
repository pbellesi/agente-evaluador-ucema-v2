from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app_v2.py"


def test_streamlit_app_v2_renders_cleanly():
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.title) > 0
    assert "Agente Evaluador UCEMA V2" in at.title[0].value
