from dataclasses import dataclass
from itertools import chain, count, product, zip_longest
import re
from typing import Dict, List, Optional, Tuple, Union

from openai import ChatCompletion

from .utils import calls_oai_api, excel_style_column_name_seq, maybe_find_backtick_block

from .api_client import OpenAIClient

from .displays import BaseDisplay, get_registered_display

FollowupKey = Optional[Tuple[str, Optional[int]]]

_CODE_START_MARKER = "---cell-start---"
_CODE_END_MARKER = "---cell-end---"


@dataclass
class Conversation:
    """
    We assume all conversations have the role sequence: system, user, assistant, user, assistant, ...
    """

    key: str
    system_message: str
    user_messages: List[str]
    assistant_messages: List[str]

    def to_messages(self) -> List[Dict]:
        messages = [
            ("system", self.system_message),
            *filter(
                None,
                chain.from_iterable(
                    zip_longest(
                        (("user", um) for um in self.user_messages),
                        (("assistant", am) for am in self.assistant_messages),
                    )
                ),
            ),
        ]
        messages = [{"role": role, "content": content} for role, content in messages]
        return messages

    def add_prompt(self, prompt: str, is_code_req: bool, ipy_history: List[Tuple]):
        if len(ipy_history) > 0:
            cell_history = "\n".join(
                [
                    f"In[{i}]: {inp}\nOut[{i}]: {outp}"
                    for i, (inp, outp) in enumerate(ipy_history)
                ]
            )
            prompt = f"""
I am going to give you the inputs and output of some Jupyter notebook cells, then make a request. Use the cell inputs/outputs as context to respond to the request.

CELL HISTORY:
{cell_history}

REQUEST:
{prompt}"""

        if is_code_req:
            self.system_message = f"You are a helpful Python data science coding assistant. You are helping the user to write code which runs in a Jupyter notebook cell. If the user asks you to do something, interpret this as a request to provide code which does that thing. For example if the user asks for the time, you should provide code which prints the current time. At the end of each response you must include a block which starts with '{_CODE_START_MARKER}' (followed by a newline) and ends with '{_CODE_END_MARKER}'. This block should contain the code which you want to put in the IPython cell. Only valid, executable Python code should appear between these two markers. No backticks."
        self.user_messages.append(prompt)

    @calls_oai_api
    def do_completion(
        self, model, temperature=None, max_tokens=None, stream: bool = False
    ):
        kwargs = {
            "model": model,
            "messages": self.to_messages(),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        api_resp = ChatCompletion.create(**kwargs, stream=stream)

        if stream:
            partial_resp = ""
            for chunk in api_resp:
                partial_resp += chunk['choices'][0]['delta'].get("content", "")
                yield partial_resp
            chat_response = partial_resp
        else:
            chat_response = api_resp["choices"][0]["message"]["content"]

        # json_body = {
        #     "model": model,
        #     "messages": self.to_messages(),
        # }

        # if temperature:
        #     json_body["temperature"] = temperature
        # if max_tokens:
        #     json_body["max_tokens"] = max_tokens

        # client = OpenAIClient()
        # resp = client.request("POST", "/chat/completions", json_body=json_body)
        self.assistant_messages.append(chat_response)

    def get_message(self, msg_idx: int = -1):
        return self.assistant_messages[msg_idx]

    def get_message_key(self, msg_idx: int = -1):
        msg_idx = msg_idx if msg_idx >= 0 else len(self.user_messages) + msg_idx
        return self.key + str(msg_idx)

    def get_code(self, msg_idx: int = -1):
        msg = self.assistant_messages[msg_idx]

        pattern = rf"{_CODE_START_MARKER}\s*(.*?)\s*{_CODE_END_MARKER}"
        matches = re.findall(pattern, msg, flags=re.DOTALL)

        # code = msg.split(_CODE_START_MARKER)[1].split(_CODE_END_MARKER)
        if len(matches) >= 1:
            code = matches[0]
            # GPT may ignore our instruction not to wrap the code in backticks.
            bt_block = maybe_find_backtick_block(code)
            return bt_block if bt_block is not None else code

        # GPT has ignored our instructions, attempt to recover some code from the cell,
        # by looking for a block like '```[python]<code>```'
        bt_block = maybe_find_backtick_block(msg)
        if bt_block is not None:
            return bt_block

        outp = "FAILED TO EXTRACT CODE.\nFull GPT Response:\n" + msg
        return "\n".join(["#" + line for line in outp.split("\n")])

    def truncate_to(self, n: int):
        self.user_messages = self.user_messages[: n + 1]
        self.assistant_messages = self.assistant_messages[: n + 1]


@dataclass
class GPTMagicState:
    # openai_api_key: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    default_system_message: str = "You are a python data science coding assistant"
    conversations = {}
    convo_key_generator = excel_style_column_name_seq()
    last_convo_key: Optional[str] = None
    display: BaseDisplay = get_registered_display()

    def get_convo(self, followup_key: FollowupKey) -> Conversation:
        convo_key, msg_key = followup_key

        if convo_key is None:
            convo_key = next(self.convo_key_generator)
            convo = Conversation(
                key=convo_key,
                system_message=self.default_system_message,
                user_messages=[],
                assistant_messages=[],
            )
            self.conversations[convo_key] = convo

        convo = self.conversations[convo_key]
        if msg_key is not None:
            convo.truncate_to(msg_key)

        self.last_convo_key = convo.key
        return convo

    # def prep_convo(self, prompt: str, model: str, followup_key: FollowupKey,
    #                is_code_req: bool) -> Conversation:
    #     convo = self.get_convo(followup_key)
    #     convo.add_prompt(prompt, is_code_req)
    #     self.last_convo_key = convo.key
    #     return convo
