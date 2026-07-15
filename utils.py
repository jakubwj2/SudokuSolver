from kivy.app import App


def get_app_or_throw() -> App:
    app = App.get_running_app()
    if not isinstance(app, App):
        raise RuntimeError("App is not running")
    return app
