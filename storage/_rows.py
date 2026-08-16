from models.common.source_location import SourceLocation


def location_columns(location: SourceLocation) -> tuple[int, int, int, int]:
    return (
        location.start_line,
        location.end_line,
        location.start_byte,
        location.end_byte,
    )


def source_location_from_row(row) -> SourceLocation:
    return SourceLocation(
        start_line=row["start_line"],
        end_line=row["end_line"],
        start_byte=row["start_byte"],
        end_byte=row["end_byte"],
    )
