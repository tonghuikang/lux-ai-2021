import re


def circle(x: int, y: int) -> str:
    return f"dc {x} {y}"

def x(x: int, y: int) -> str:
    return f"dx {x} {y}"

def line(x1: int, y1: int, x2: int, y2: int) -> str:
    return f"dl {x1} {y1} {x2} {y2}"

# text at cell on map
def text(x: int, y: int, message: str, fontsize: int = 16) -> str:
    return f"dt {x} {y} {fontsize} '{message}'"

# text besides map
def sidetext(message: str) -> str:
    return f"dst '{message}'"


def pretty_print(obj, indent=1, rec=0, key=''):
    # https://stackoverflow.com/questions/51753937/python-pretty-print-nested-objects
    s_indent = ' ' * indent * rec
    items = {}
    stg = s_indent

    if key != '': stg += str(key) + ': '

    # Discriminate && Check if final
    if isinstance(obj, list):
        items = enumerate(obj)
    elif isinstance(obj, dict):
        items = obj.items()
    elif '__dict__' in dir(obj):
        items = obj.__dict__.items()
    if not items:
        return stg + str(obj)

    # Recurse
    stg += '(' + type(obj).__name__ + ')\n'
    for k, v in items:
        stg += pretty_print(v, indent=indent, rec=rec+1, key=k) + "\n"

    # Return without empty lines
    return re.sub(r'\n\s*\n', '\n', stg)[:-1]
