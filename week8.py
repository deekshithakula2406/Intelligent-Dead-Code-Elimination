import tkinter as tk
from tkinter import scrolledtext, messagebox
import re

# SYNTAX CHECKER (Week 6)
def check_syntax(lines):
    for line in lines:
        line = line.strip()

        if (line.startswith("int") or line.startswith("float")) and not line.endswith(";"):
            return False, f"Syntax Error: Missing ';' → {line}"

        if line.startswith("return") and not line.endswith(";"):
            return False, f"Syntax Error: Missing ';' in return → {line}"

    return True, "Syntax OK"


# AST NODE
class ASTNode:
    def __init__(self, node_type, value=None, children=None):
        self.node_type = node_type
        self.value = value
        self.children = children if children else []

    def __str__(self, level=0):
        ret = "  " * level + f"{self.node_type}: {self.value}\n"
        for child in self.children:
            ret += child.__str__(level + 1)
        return ret


# CFG NODE (Week 7)
class CFGNode:
    def __init__(self, name):
        self.name = name
        self.edges = []

    def add_edge(self, node):
        self.edges.append(node)


def analyze_code():
    source = code_input.get("1.0", tk.END)

    cfg_output.config(state="normal")
    cfg_output.delete("1.0", tk.END)

    dead_code_output.config(state="normal")
    dead_code_output.delete("1.0", tk.END)

    explanation_output.config(state="normal")
    explanation_output.delete("1.0", tk.END)

    ast_output.config(state="normal")
    ast_output.delete("1.0", tk.END)
    lines = source.splitlines()

    # SYNTAX CHECK
    ok, msg = check_syntax(lines)
    if not ok:
        messagebox.showerror("Syntax Error", msg)
        return

    # AST GENERATION
    ast_root = ASTNode("Program")

    for line in lines:
        line = line.strip()

        if (line.startswith("int") or line.startswith("float")) and "=" in line:
            tokens = re.findall(r"[a-zA-Z_]\w*|\d+", line)
            if len(tokens) >= 3:
                var = tokens[1]
                val = tokens[2]
                ast_root.children.append(
                    ASTNode("Declaration", var, [
                        ASTNode("Value", val)
                    ])
                )

        elif "=" in line and not line.startswith("int") and not line.startswith("float"):
            left, right = line.split("=", 1)
            lhs = left.strip()
            rhs_tokens = re.findall(r"[a-zA-Z_]\w*|\d+|\+", right)

            if "+" in rhs_tokens and len(rhs_tokens) >= 3:
                ast_root.children.append(
                    ASTNode("Assignment", lhs, [
                        ASTNode("Add", "+", [
                            ASTNode("Identifier", rhs_tokens[0]),
                            ASTNode("Constant", rhs_tokens[2])
                        ])
                    ])
                )

        elif line.startswith("return"):
            tokens = re.findall(r"[a-zA-Z_]\w*", line)
            if len(tokens) >= 2:
                ast_root.children.append(
                    ASTNode("Return", tokens[1])
                )

    # CFG CONSTRUCTION
    entry = CFGNode("Entry")
    exit_node = CFGNode("Exit")

    current = entry
    block_count = 1

    for line in lines:
        line = line.strip()

        if line.startswith("if"):
            condition_node = CFGNode(f"If_Block_{block_count}")
            current.add_edge(condition_node)

            true_block = CFGNode(f"If_True_{block_count}")
            false_block = CFGNode(f"If_False_{block_count}")

            condition_node.add_edge(true_block)
            condition_node.add_edge(false_block)

            true_block.add_edge(exit_node)
            false_block.add_edge(exit_node)

            current = exit_node
            block_count += 1

        elif line.startswith("while"):
            loop_node = CFGNode(f"While_Block_{block_count}")
            current.add_edge(loop_node)

            body_node = CFGNode(f"While_Body_{block_count}")
            loop_node.add_edge(body_node)

            body_node.add_edge(loop_node)
            loop_node.add_edge(exit_node)

            current = exit_node
            block_count += 1

        else:
            basic_block = CFGNode(f"BasicBlock_{block_count}")
            current.add_edge(basic_block)
            current = basic_block
            block_count += 1

    current.add_edge(exit_node)
    
    # DEAD CODE ANALYSIS
        # ---------- CLASSICAL DCE (Week 8) ----------
    statements = []

    for line in lines:
        line = line.strip()
        if line:
            statements.append(line)

    live = set()
    dead_assignments = []

    for line in reversed(statements):

        # Assignment
        if "=" in line :
            left, right = line.split("=", 1)
            var = left.strip()

            used_vars = re.findall(r"[a-zA-Z_]\w*", right)

            # If variable not live → dead
            if var not in live:
                dead_assignments.append(line)

            live.discard(var)
            live.update(used_vars)

        # Return
        elif line.startswith("return"):
            vars_used = re.findall(r"[a-zA-Z_]\w*", line)
            live.update(vars_used)

    dead = dead_assignments

    # CFG OUTPUT
    def print_cfg(node, visited=None):
        if visited is None:
            visited = set()
        if node in visited:
            return ""
        visited.add(node)

        output = ""
        for edge in node.edges:
            output += f"{node.name} → {edge.name}\n"
            output += print_cfg(edge, visited)
        return output

    cfg_text = print_cfg(entry)

    cfg_output.insert(tk.END, "Control Flow Graph (CFG)\n")
    cfg_output.insert(tk.END, "---------------------------------\n")
    cfg_output.insert(tk.END, cfg_text)

    # DEAD CODE OUTPUT
    dead_code_output.insert(
        tk.END,
        "Dead Code Identified\n"
        "---------------------------------\n"
    )

    if not dead:
        dead_code_output.insert(tk.END, "No dead assignments detected\n")
    else:
        for stmt in dead:
            dead_code_output.insert(tk.END, f"Dead: {stmt}\n")

    # EXPLANATION
    explanation_output.insert(
        tk.END,
        "Explanation\n"
        "---------------------------------\n"
        "• Two-pass static analysis\n"
        "• AST-based structure analysis\n"
        "• RHS and return usage tracking\n"
        "• Classical dead code elimination\n"
    )
   # AST OUTPUT
    ast_output.insert(tk.END, str(ast_root))

# Disable outputs
    cfg_output.config(state="disabled")
    dead_code_output.config(state="disabled")
    explanation_output.config(state="disabled")
    ast_output.config(state="disabled")

#GUI

root = tk.Tk()
root.title("Intelligent Dead Code Elimination (IDCE)")
root.geometry("900x650")

tk.Label(root, text="Intelligent Dead Code Elimination System",
         font=("Arial", 16, "bold")).pack(pady=10)

tk.Label(root, text="Input C-like Source Code").pack(anchor="w", padx=10)
code_input = scrolledtext.ScrolledText(root, height=10)
code_input.pack(fill=tk.BOTH, padx=10, pady=5)

tk.Button(root, text="Analyze Code",
          command=analyze_code,
          bg="lightblue",
          font=("Arial", 12)).pack(pady=10)

tk.Label(root, text="Control Flow Graph (CFG)").pack(anchor="w", padx=10)
cfg_output = scrolledtext.ScrolledText(root, height=5,state="disabled")
cfg_output.pack(fill=tk.BOTH, padx=10, pady=5)

tk.Label(root, text="Dead Code Elimination Result").pack(anchor="w", padx=10)
dead_code_output = scrolledtext.ScrolledText(root, height=5,state="disabled")
dead_code_output.pack(fill=tk.BOTH, padx=10, pady=5)

tk.Label(root, text="Explanation Panel").pack(anchor="w", padx=10)
explanation_output = scrolledtext.ScrolledText(root, height=6,state="disabled")
explanation_output.pack(fill=tk.BOTH, padx=10, pady=5)

tk.Label(root, text="Abstract Syntax Tree (AST)").pack(anchor="w", padx=10)
ast_output = scrolledtext.ScrolledText(root, height=8,state="disabled")
ast_output.pack(fill=tk.BOTH, padx=10, pady=5)

root.mainloop()



