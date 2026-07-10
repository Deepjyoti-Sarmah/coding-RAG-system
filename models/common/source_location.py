from dataclasses import dataclass


@dataclass(slots=True)
class SourceLocation:
    start_line: int
    end_line: int

    start_byte: int
    end_byte: int
