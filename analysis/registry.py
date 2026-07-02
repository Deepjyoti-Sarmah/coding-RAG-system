from analysis.handlers.
from analysis.handlers.class import handle_classclass import handle_class
from analysis.handlers.classes import handle_class
from analysis.handlers.function import handle_function
from analysis.handlers.variable import handle_varibale_declarator


NODE_HANDLERS = {
    "function_declaration": handle_function,
    "variable_declaration": handle_varibale_declarator,
    "class_declaration": handle_class,
    "interface_declaration": handle_interface,
    "type_alias_declaration": handle_type_alias,
    "method_definition": handle_method,
}
