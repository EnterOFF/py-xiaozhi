# 设备激活界面包
__all__ = ["ActivationWindow"]


def __getattr__(name):
    if name == "ActivationWindow":
        from .activation_window import ActivationWindow

        return ActivationWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
