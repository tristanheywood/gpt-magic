from itertools import count, product
import re
from typing import Optional

from IPython.core.getipython import get_ipython
from operator import itemgetter


def get_ipython_history(last_n: int = 1):
    ipy = get_ipython()
    execution_count = ipy.execution_count

    input_history = list(ipy.history_manager.get_range(stop=-1))[-last_n:]
    output_history = [ipy.user_ns["_oh"].get(n_exec) for _, n_exec, _ in input_history]

    return list(zip(map(itemgetter(-1), input_history), output_history))


def excel_style_column_name_seq():
    capital_alphabet = tuple(map(chr, range(ord("A"), ord("Z") + 1)))
    for n in count(1):
        for x in product(*[capital_alphabet] * n):
            yield "".join(x)


def maybe_find_backtick_block(s: str) -> Optional[str]:
    """Find the last backtick block in a string, if any.
    
    Will return <content> in the cases ```\n<content>\n``` and ```python\n<content>\n```.
    """

    pattern = r"(?P<start>```python\n|```\n)(?P<code>.*?)(?P<end>\n```)"
    matches = list(re.finditer(pattern, s, flags=re.DOTALL))
    if len(matches) >= 1:
        return matches[-1].group("code")
    
    return None