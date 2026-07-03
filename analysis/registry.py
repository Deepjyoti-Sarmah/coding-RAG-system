from analysis.handlers.classes import handle_class
from analysis.handlers.function import handle_function
from analysis.handlers.method import handle_method
from analysis.handlers.variable import handle_varibale_declarator


NODE_HANDLERS = {
    "function_declaration": handle_function,
    "class_declaration": handle_class,
    "method_definition": handle_method,
    "variable_declaration": handle_varibale_declarator,
    # "interface_declaration": handle_interface,
    # "type_alias_declaration": handle_type_alias,
}
