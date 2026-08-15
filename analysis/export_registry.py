from analysis.export_handlers.declaration import handle_export_statement
from analysis.export_handlers.specifier import handle_export_specifier


EXPORT_HANDLERS = {
    "export_statement": handle_export_statement,
    "export_specifier": handle_export_specifier,
}
