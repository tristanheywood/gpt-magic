import argparse
from time import time
import re
import shlex
from getpass import getpass
from typing import Dict, Optional

from .utils import calls_oai_api, get_available_models, get_ipython_history

from IPython.display import clear_output, display, Markdown

from .gpt_state import GPTMagicState

from .displays import get_registered_display

from .api_client import OpenAIClient


def _parse_args(line):
    parser = argparse.ArgumentParser(prog="%%gpt")
    parser.add_argument("prompt", nargs="?", default=None, help="Prompt for GPT.")
    # parser.add_argument(
    #     "--login",
    #     "-l",
    #     action="store_true",
    #     help="Provide your OpenAI API Key (required to use GPT).",
    # )
    # 3 State option: -f not present => args.folloup == None,
    # -f present => args.followup == "", -f present with value => args.followup == value
    parser.add_argument(
        "--followup",
        "-f",
        help="Continue the conversation.",
        nargs="?",
        const="",
        default=None,
    )
    parser.add_argument(
        "--code",
        "-c",
        action="store_true",
        help="Generate executable Python code based on <prompt> and put it in this cell.",
    )
    parser.add_argument(
        "--model",
        "-m",
        help="The OpenAI model to use. If provided with no arguments, lists available models.",
        nargs="?",
        const="",
    )
    parser.add_argument(
        "--show",
        "-s",
        help="Show the previous cell(s) inputs and outputs to GPT, to provide context for the prompt. Note: only cell outputs are passed, not stdout.",
        nargs="?",
        const="",
        default=None,
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Print debug information about the request and response (including the full conversation history passed to the API.)",
    )
    # parser.add_argument(
    #     "--new",
    #     "-n",
    #     help="Start a brand new conversation without previous context",
    #     action="store_true",
    # )
    # parser.add_argument(
    #     "--temperature",
    #     help="What sampling temperature to use, between 0 and 2. See OpenAI docs",
    #     type=float,
    # )
    # parser.add_argument(
    #     "--max-tokens",
    #     help="The maximum number of tokens to generate in the chat completion.",
    #     type=int,
    # )
    # parser.add_argument(
    #     "--system-message",
    #     help=
    #     "The initial system message used to start the conversation. Use `--no-system-message` to skip it.",
    # )
    # parser.add_argument(
    #     "--model",
    #     help=
    #     "The OpenAI model to use. Use `%chat_models` to display the available ones",
    # )
    args = parser.parse_args(shlex.split(line))

    # If -f is being used as a flag, it may steal the prompt. Detect and correct this.
    if args.prompt is None:
        if args.followup is not None:
            args.prompt = args.followup
            args.followup = ""
        elif args.show is not None:
            args.prompt = args.show
            args.show = ""

    return args


# def _get_messages(context: Dict,
#                   prompt: str,
#                   request_code: bool,
#                   system_message: Optional[str] = None,
#                   reset_conversation: bool = False):
#     message_history = context["message_history"]
#     if reset_conversation:
#         message_history = []

#     system_message = (system_message
#                       or context["config"]["default_system_message"])

#     if request_code:
#         system_message = f"You are a helpful Python data science coding assistant. You are helping the user to write code which runs in a Jupyter notebook cell. If the user asks you to do something, interpret this as a request to provide code which does that thing. For example if the user asks for the time, you should provide code which prints the current time. At the end of each response you must include a block which starts with '{_CODE_START_MARKER}' (followed by a newline) and ends with '{_CODE_END_MARKER}'. This block should contain the code which you want to put in the IPython cell. Only valid, executable Python code should appear between these two markers. No backticks."

#     if len(message_history) == 0:
#         message_history = [None]

#     # Note: This overrides the system message of existing conversations.
#     message_history[0] = {"role": "system", "content": system_message}

#     messages = message_history + [{"role": "user", "content": prompt}]

#     return messages

# def _get_response(messages,
#                   context,
#                   client: OpenAIClient,
#                   temperature=None,
#                   max_tokens=None):

#     json_body = {
#         "model": context["config"]["default_model"],
#         "messages": messages
#     }

#     if temperature:
#         json_body["temperature"] = temperature
#     if max_tokens:
#         json_body["max_tokens"] = max_tokens

#     resp = client.request("POST", "/chat/completions", json_body=json_body)
#     chat_response = resp["choices"][0]["message"]["content"]
#     new_messages = messages + [
#         {
#             "role": "assistant",
#             "content": chat_response
#         },
#     ]

#     return chat_response, new_messages


# @calls_oai_api
# def _get_available_models(api_key: str):
#     client = OpenAIClient(api_key)
#     resp = client.request("GET", "/models")
#     models = [m["id"] for m in resp["data"] if m["id"].startswith("gpt")]
#     return models


@calls_oai_api
def _login_command():
    # state.openai_api_key = getpass("Enter your OpenAI API Key: ")
    models = get_available_models()
    formatted_models = "\n".join([f"\t- {model}" for model in models])
    return f"##### Available models:\n\n{formatted_models}"


def _code_command(prompt: str, history, client: OpenAIClient):
    pass


def _text_command(prompt: str, history, client: OpenAIClient):
    pass


def gpt_command(state: GPTMagicState, line, cell=None):
    ipy_display = get_registered_display()

    try:
        args = _parse_args(line)
    except SystemExit as e:
        # Assume this was caused by `--help`.
        return

    if args.debug:
        print("Arguments:", args)

    # if state.openai_api_key is None or args.login:
    #     ipy_display.display(_login_command(state))

    if args.model is not None:
        avail_models = get_available_models()
        if args.model == "":
            print("Available models: ", *["• " + m for m in avail_models], sep="\n")
            return
        else:
            model = args.model
            if model not in avail_models:
                choices = [m for m in avail_models if m.endswith(model)]
                if len(choices) == 0:
                    raise ValueError(f"Model {model} not found.")
                model = choices[0]
    else:
        model = state.default_model

    # messages = _get_messages(context,
    #                          args.prompt,
    #                          request_code=args.code,
    #                          reset_conversation=not args.followup)

    followup_key = args.followup
    if followup_key == "":
        convo_key = state.last_convo_key
        msg_key = None
    elif followup_key is not None:
        convo_key, msg_key = re.match(r"([A-Z]+)(\d*)", followup_key).groups()
        msg_key = int(msg_key) if msg_key else None
    else:
        convo_key = None
        msg_key = None
    followup_key = (convo_key, msg_key)

    ipy_history = []
    if args.show is not None:
        last_n = 1 if args.show == "" else int(args.show)
        ipy_history = get_ipython_history(last_n)

    convo = state.get_convo(followup_key)
    convo.add_prompt(args.prompt, args.code, ipy_history)

    # convo = state.prep_convo(args.prompt, model, followup_key, args.code)

    if args.debug:
        print("Using model:", model)
        print("Continuing conversation:", convo.get_message_key())
        ipy_display.display(convo.to_messages())

    t_last_update = time()
    for partial_resp in convo.do_completion(model, stream=True):
        clear_output(wait=True)
        t_now = time()
        # Update every 100 ms
        if t_now - t_last_update > 0.1:
            display(Markdown(partial_resp))
            t_last_update = t_now
    clear_output(wait=False)

    # gpt_resp, new_history = _get_response(messages, context, client,
    #                                       args.temperature, args.max_tokens)
    if args.debug:
        print("RESPONSE:", convo.assistant_messages[-1])
    # context["message_history"] = new_history

    if args.code:
        # code_resp = gpt_resp[gpt_resp.index(_CODE_START_MARKER) +
        #                      len(_CODE_START_MARKER):gpt_resp.
        #                      index(_CODE_END_MARKER)]
        code_resp = convo.get_code()
        get_ipython().set_next_input(f"#%gpt {line}\n{code_resp}", replace=True)
    else:
        ipy_display.display(f"GPT[{convo.get_message_key()}]: " + convo.get_message())
    return
