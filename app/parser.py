import ast
import re


def get_added_lines(patch: str) -> set:
    """
    Reads a GitHub patch and returns a set of line numbers that were newly added.
    """
    added_lines = set()
    if not patch or patch == "No patch available":
        return added_lines

    current_line_num = 0
    for line in patch.split('\n'):
        match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
        if match:
            current_line_num = int(match.group(1))
            continue
        
        if line.startswith('+++') or line.startswith('---'):
            continue
        
        if line.startswith('+'):
            added_lines.add(current_line_num)
            current_line_num += 1
        elif line.startswith(' '):
            current_line_num += 1
            
    return added_lines


class ArchGuardVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = [] 
        self.classes = []
        self.imports = []

    def visit_FunctionDef(self, node):

        self.functions.append({
            'name': node.name, 
            'start': node.lineno, 
            'end': getattr(node, 'end_lineno', node.lineno),
            'node': node 
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions.append({
            'name': node.name, 
            'start': node.lineno, 
            'end': getattr(node, 'end_lineno', node.lineno),
            'node': node
        })
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append({
            'name': node.name, 
            'start': node.lineno, 
            'end': getattr(node, 'end_lineno', node.lineno),
            'node': node
        })
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module if node.module else ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)


def analyze_python_file(full_code: str, patch: str) -> dict:
    """
    Combines the exact code block (State) with the diff patch (Delta)
    to create a highly targeted payload for Layer 3.
    """
    if not full_code:
        return {"status": "skipped", "reason": "No code provided"}
        
    added_lines = get_added_lines(patch)
    
    try:
        tree = ast.parse(full_code)
        visitor = ArchGuardVisitor()
        visitor.visit(tree)
        
        impacted_functions = []
        for func in visitor.functions:
            if any(func['start'] <= line <= func['end'] for line in added_lines):

                exact_code = ast.get_source_segment(full_code, func['node'])
                
                impacted_functions.append({
                    "function_name": func['name'],
                    "full_function_context": exact_code
                })
                
        impacted_classes = []
        for cls in visitor.classes:
            if any(cls['start'] <= line <= cls['end'] for line in added_lines):
                exact_code = ast.get_source_segment(full_code, cls['node'])
                
                impacted_classes.append({
                    "class_name": cls['name'],
                    "full_class_context": exact_code
                })
                
        return {
            "status": "success",
            "impacted_functions": impacted_functions,
            "impacted_classes": impacted_classes,
            "file_imports": list(set(visitor.imports)),
            "what_actually_changed_diff": patch
        }
    except SyntaxError as e:
        return {"status": "error", "message": f"Syntax Error: {str(e)}"}

