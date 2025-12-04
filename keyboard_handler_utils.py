from typing import Callable, Dict, Tuple, Union

modifier_and_key_to_func: Dict[Tuple[Tuple[str, ...], str], Callable[[], None]] = {}


def register_hotkey(modifiers: Union[str, Tuple[str, ...]], key: str):
    def register_hotkey_inner(func: Callable[[], None]):
        _modifiers = (modifiers,) if isinstance(modifiers, str) else modifiers
        modifier_and_key_to_func[_modifiers, key] = func

        return func

    return register_hotkey_inner


@register_hotkey(('F13', 'F14'), 'A')
def example_hotkey_function():
    ...