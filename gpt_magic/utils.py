from itertools import count, product

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
