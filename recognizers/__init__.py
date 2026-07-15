from kivy.utils import platform
from recognizers.protocol import DigitRecognizer


def get_digit_recognizer() -> DigitRecognizer:
    if platform == "android":
        from recognizers.android_recognizer import AndroidRecognizer

        return AndroidRecognizer()

    from recognizers.desktop_recognizer import DesktopRecognizer

    return DesktopRecognizer()
