from dataclasses import dataclass


@dataclass
class Utterance:
    ts: str
    speaker: str
    text: str
