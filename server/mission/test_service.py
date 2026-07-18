from . import service


def test_start_returns_first_step():
    result = service.start("kiosk_cafe")
    assert result["step"] == 0
    assert result["options"]


def test_correct_answer_advances():
    result = service.handle_step("kiosk_cafe", 0, "매장에서 먹기")
    assert result["correct"] is True
    assert result["done"] is False
    assert result["step"] == 1


def test_wrong_answer_stays_on_step():
    result = service.handle_step("kiosk_cafe", 0, "포장하기")
    assert result["correct"] is False
    assert result["step"] == 0


def test_final_step_completes():
    result = service.handle_step("kiosk_cafe", 2, "아니오")
    assert result["correct"] is True
    assert result["done"] is True
