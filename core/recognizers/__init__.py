from kivy.utils import platform

from core.recognizers.protocol import DigitRecognizer


def get_digit_recognizer() -> DigitRecognizer:
    if platform == "android":
        from core.recognizers.android_recognizer import AndroidRecognizer

        return AndroidRecognizer()

    from core.recognizers.desktop_recognizer import DesktopRecognizer

    return DesktopRecognizer()
