from analysis.import_handlers.default import handle_default_import
from analysis.import_handlers.named import handle_import_specifier
from analysis.import_handlers.namespace import handle_namespace_import

IMPORT_HANDLERS = {
    "import_specifier": handle_import_specifier,
    "import_clause": handle_default_import,
    "namespace_import": handle_namespace_import,
}
