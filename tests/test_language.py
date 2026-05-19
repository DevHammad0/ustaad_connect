from src.api.agent import detect_language

def test_detect_language_urdu():
    assert detect_language("مجھے اے سی ٹھیک کروانا ہے") == "urdu"

def test_detect_language_roman_urdu():
    assert detect_language("mujhe ac ka masla hai") == "roman_urdu"
    assert detect_language("apni location share karein") == "roman_urdu"
    assert detect_language("niche diye gaye button par click kare") == "roman_urdu"

def test_detect_language_english():
    assert detect_language("my ac is not cooling properly") == "english"
    assert detect_language("please find a plumber near me") == "english"
    assert detect_language("how much is the visit fee") == "english"

def test_detect_language_empty_and_fallback():
    assert detect_language("") == "english"
    assert detect_language(None) == "english"

def test_detect_language_system_info_stripping():
    # Even if there are words in system info, it should strip it and detect based on the remaining text.
    text_roman = "masla hai [System Info: Customer Phone is 923038571702, Message Type is text]"
    assert detect_language(text_roman) == "roman_urdu"

    text_english = "my ac cooling [System Info: Customer Phone is 923038571702, Message Type is text]"
    assert detect_language(text_english) == "english"
