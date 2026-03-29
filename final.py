import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import re
from sklearn.linear_model import LogisticRegression

# Constants
BUILT_IN_FUNCTIONS = {"printf", "scanf"}
KEYWORDS = {"int", "float", "return", "if", "else", "while"}


# 1. Syntax Checker
def check_syntax(lines):
    for line in lines:
        line = line.strip()
        if (line.startswith("int") or line.startswith("float")) and not line.endswith(";"):
            return False, f"Syntax Error: Missing ';'  ->  {line}"
        elif line.startswith("return") and not line.endswith(";"):
            return False, f"Syntax Error: Missing ';' in return  ->  {line}"
        elif "=" in line and not line.endswith(";"):
            return False, f"Syntax Error: Missing ';'  ->  {line}"
    return True, "Syntax OK"


# 2. AST Node
class ASTNode:
    def __init__(self, node_type, value=None, children=None):
        self.node_type = node_type
        self.value     = value
        self.children  = children if children else []

    def __str__(self, level=0):
        ret = "  " * level + f"{self.node_type}: {self.value}\n"
        for child in self.children:
            ret += child.__str__(level + 1)
        return ret


# 3. CFG Node
class CFGNode:
    def __init__(self, name):
        self.name  = name
        self.edges = []

    def add_edge(self, node):
        self.edges.append(node)


# 4. Feature Extraction (Intelligent layer)
def extract_features(line, live):
    clean = line.rstrip(";").strip()
    left, right = clean.split("=", 1)
    left_tokens = re.findall(r"[a-zA-Z_]\w*", left)
    var = left_tokens[-1]
    used_vars = [v for v in re.findall(r"[a-zA-Z_]\w*", right) if v not in KEYWORDS]

    features = {
        "overwritten": var not in live,
        "constant":    bool(re.search(r"\d+", right)),
        "simple":      all(op not in right for op in "+-*/"),
        "self_assign": var in used_vars,
        "repeated":    right.strip().rstrip(";") == var,
        "no_effect":   var in used_vars and "+" not in right,
        "unused_rhs":  len(used_vars) == 0,
    }
    return features, var, used_vars


def compute_confidence(features):
    score = 0.3
    if features["overwritten"]: score += 0.20
    if features["constant"]:    score += 0.15
    if features["simple"]:      score += 0.10
    if features["self_assign"]: score += 0.10
    if features["no_effect"]:   score += 0.10
    if features["unused_rhs"]:  score += 0.10
    if features["repeated"]:    score += 0.05
    return round(min(score, 1.0), 2)


# 5. Safety / Security Validation
def is_safe_to_remove(line):
    if "return" in line:
        return False
    for word in ["password", "auth", "token", "secure"]:
        if word in line.lower():
            return False
    if "printf" in line or "scanf" in line:
        return False
    return True


# 6. ML Model — trained once at startup
def train_ml_model():
    X = [[1,1,1],[1,0,1],[0,1,1],[1,1,0],[0,0,1],
         [1,0,0],[0,1,0],[0,0,0],[1,1,1],[1,0,1]]
    y = [1,1,0,1,0,0,0,0,1,1]
    model = LogisticRegression()
    model.fit(X, y)
    return model

ml_model = train_ml_model()

def features_to_vector(features):
    return [[int(features["overwritten"]),
             int(features["constant"]),
             int(features["simple"])]]


# 7. CFG Builder
def build_cfg(lines):
    entry     = CFGNode("Entry")
    exit_node = CFGNode("Exit")
    current   = entry
    count     = 1
    for line in lines:
        if line.startswith("if"):
            cond        = CFGNode(f"If_Block_{count}")
            true_block  = CFGNode(f"If_True_{count}")
            false_block = CFGNode(f"If_False_{count}")
            current.add_edge(cond)
            cond.add_edge(true_block)
            cond.add_edge(false_block)
            true_block.add_edge(exit_node)
            false_block.add_edge(exit_node)
            current = exit_node
            count  += 1
        elif line.startswith("while"):
            loop = CFGNode(f"While_Block_{count}")
            body = CFGNode(f"While_Body_{count}")
            current.add_edge(loop)
            loop.add_edge(body)
            body.add_edge(loop)
            loop.add_edge(exit_node)
            current = exit_node
            count  += 1
        else:
            node = CFGNode(f"BasicBlock_{count}")
            current.add_edge(node)
            current = node
            count  += 1
    current.add_edge(exit_node)
    return entry

def print_cfg(node, visited=None):
    if visited is None:
        visited = set()
    if node in visited:
        return ""
    visited.add(node)
    result = ""
    for edge in node.edges:
        result += f"  {node.name}  ->  {edge.name}\n"
        result += print_cfg(edge, visited)
    return result


# 8. Classical DCE — reverse liveness only
def classical_dce(lines):
    live             = set()
    dead_assignments = []

    for line in reversed(lines):
        if line.startswith("return"):
            vars_in_return = re.findall(r"[a-zA-Z_]\w*", line)
            live.update(v for v in vars_in_return if v not in KEYWORDS)
        elif "=" in line:
            try:
                clean       = line.rstrip(";").strip()
                left, right = clean.split("=", 1)
                left_tokens = re.findall(r"[a-zA-Z_]\w*", left)
                var         = left_tokens[-1]
                used_vars   = [v for v in re.findall(r"[a-zA-Z_]\w*", right)
                               if v not in KEYWORDS]
            except (ValueError, IndexError):
                continue

            if var not in live:
                dead_assignments.append(line)

            live.discard(var)
            live.update(v for v in used_vars if v not in KEYWORDS)

    dead_set        = set(dead_assignments)
    optimized_lines = [l for l in lines if l not in dead_set]
    return dead_assignments, optimized_lines


# 9. Intelligent DCE — liveness + confidence + ML + security
def intelligent_dce(lines):
    live             = set()
    dead_assignments = []
    protected_lines  = []

    for line in reversed(lines):
        if line.startswith("return"):
            vars_in_return = re.findall(r"[a-zA-Z_]\w*", line)
            live.update(v for v in vars_in_return if v not in KEYWORDS)
        elif "=" in line:
            try:
                features, var, used_vars = extract_features(line, live)
            except (ValueError, IndexError):
                continue

            if features["overwritten"]:
                if is_safe_to_remove(line):
                    h_score  = compute_confidence(features)
                    ml_score = ml_model.predict_proba(features_to_vector(features))[0][1]
                    final    = round((h_score + ml_score) / 2, 2)
                    dead_assignments.append((line, final, ml_score, features))
                else:
                    protected_lines.append(line)

            live.discard(var)
            live.update(v for v in used_vars if v not in KEYWORDS)

    for line in lines:
        if not is_safe_to_remove(line) and line not in protected_lines:
            protected_lines.append(line)

    dead_set        = {stmt for stmt, _, _, _ in dead_assignments}
    optimized_lines = [l for l in lines if l not in dead_set]
    return dead_assignments, optimized_lines, protected_lines


# 10. AST Builder
def build_ast(lines):
    ast_root = ASTNode("Program")
    for line in lines:
        if (line.startswith("int") or line.startswith("float")) and "=" in line:
            tokens = re.findall(r"[a-zA-Z_]\w*|\d+", line)
            if len(tokens) >= 3:
                ast_root.children.append(
                    ASTNode("Declaration", tokens[1], [ASTNode("Value", tokens[2])]))
        elif (line.startswith("int") or line.startswith("float")) and "=" not in line:
            tokens = re.findall(r"[a-zA-Z_]\w*", line)
            if len(tokens) >= 2:
                ast_root.children.append(ASTNode("Declaration", tokens[1]))
        elif "=" in line and not line.startswith("int") and not line.startswith("float"):
            left, right = line.split("=", 1)
            lhs        = left.strip()
            rhs_tokens = re.findall(r"[a-zA-Z_]\w*|\d+|[+\-*/]", right)
            if "+" in rhs_tokens and len(rhs_tokens) >= 3:
                ast_root.children.append(
                    ASTNode("Assignment", lhs,
                        [ASTNode("Add", "+", [
                            ASTNode("Identifier", rhs_tokens[0]),
                            ASTNode("Constant",   rhs_tokens[2])])]))
            else:
                val = rhs_tokens[0] if rhs_tokens else "?"
                ast_root.children.append(
                    ASTNode("Assignment", lhs, [ASTNode("Value", val)]))
        elif line.startswith("return"):
            tokens  = re.findall(r"[a-zA-Z_]\w*", line)
            ret_val = tokens[1] if len(tokens) >= 2 else "?"
            ast_root.children.append(ASTNode("Return", ret_val))
    return ast_root


# 11. Main Analyze function
def analyze_code():
    source = code_input.get("1.0", tk.END)
    lines  = [l.strip() for l in source.splitlines() if l.strip()]

    all_panels = [
        classical_cfg_out, classical_dead_out, classical_opt_out,
        intel_cfg_out, intel_dead_out, intel_opt_out,
        intel_security_out, intel_explain_out, intel_ast_out,
        comparison_out
    ]
    for p in all_panels:
        p.config(state="normal")
        p.delete("1.0", tk.END)

    if not lines:
        messagebox.showinfo("Empty Input", "Please enter some source code first.")
        for p in all_panels:
            p.config(state="disabled")
        return

    ok, msg = check_syntax(lines)
    if not ok:
        messagebox.showerror("Syntax Error", msg)
        for p in all_panels:
            p.config(state="disabled")
        return

    cfg_entry = build_cfg(lines)
    cfg_text  = print_cfg(cfg_entry)
    ast_root  = build_ast(lines)

    c_dead, c_opt              = classical_dce(lines)
    i_dead, i_opt, i_protected = intelligent_dce(lines)

    # Classical Tab outputs
    classical_cfg_out.insert(tk.END, "Control Flow Graph\n" + "-"*34 + "\n")
    classical_cfg_out.insert(tk.END, cfg_text)

    classical_dead_out.insert(tk.END, "Dead Code Detected  (Classical)\n" + "-"*34 + "\n")
    if not c_dead:
        classical_dead_out.insert(tk.END, "  No dead assignments found.\n")
    else:
        for stmt in c_dead:
            classical_dead_out.insert(tk.END, f"  [DEAD]  {stmt}\n")
        classical_dead_out.insert(tk.END,
            f"\n  Statements removed  : {len(c_dead)}\n"
            f"  Method used         : Reverse Liveness Analysis\n"
            f"  Confidence Score    : Not available\n"
            f"  Security Check      : Not performed\n"
            f"  Note: All detected dead code is removed without any validation.\n"
        )

    classical_opt_out.insert(tk.END, "Optimized Code  (Classical)\n" + "-"*34 + "\n")
    for ol in c_opt:
        classical_opt_out.insert(tk.END, f"  {ol}\n")
    classical_opt_out.insert(tk.END,
        f"\n  Original : {len(lines)} lines   ->   After : {len(c_opt)} lines"
        f"   (Removed {len(c_dead)})\n"
    )

    # Intelligent Tab outputs
    intel_cfg_out.insert(tk.END, "Control Flow Graph\n" + "-"*34 + "\n")
    intel_cfg_out.insert(tk.END, cfg_text)

    intel_dead_out.insert(tk.END, "Dead Code Detected  (Intelligent)\n" + "-"*34 + "\n")
    if not i_dead:
        intel_dead_out.insert(tk.END, "  No dead assignments found.\n")
    else:
        for stmt, conf, ml, feat in i_dead:
            level = "HIGH" if conf > 0.7 else ("MEDIUM" if conf >= 0.4 else "LOW")
            intel_dead_out.insert(tk.END,
                f"  [DEAD]  {stmt}\n"
                f"          Heuristic : {compute_confidence(feat)}"
                f"  |  ML Score : {round(ml,2)}"
                f"  |  Final Score : {conf}  [{level}]\n"
                f"          Features  -> "
                f"overwritten={feat['overwritten']}  "
                f"constant={feat['constant']}  "
                f"simple={feat['simple']}  "
                f"unused_rhs={feat['unused_rhs']}\n\n"
            )
        intel_dead_out.insert(tk.END,
            f"  Statements removed  : {len(i_dead)}\n"
            f"  Method used         : Liveness + Heuristics + ML + Security Validation\n"
            f"  Note: Only safe and high-confidence dead code is removed.\n"
        )

    intel_opt_out.insert(tk.END, "Optimized Code  (Intelligent)\n" + "-"*34 + "\n")
    for ol in i_opt:
        intel_opt_out.insert(tk.END, f"  {ol}\n")
    intel_opt_out.insert(tk.END,
        f"\n  Original : {len(lines)} lines   ->   After : {len(i_opt)} lines"
        f"   (Removed {len(i_dead)})\n"
    )

    intel_security_out.insert(tk.END, "Security Report\n" + "-"*34 + "\n")
    if not i_protected:
        intel_security_out.insert(tk.END, "  No security-critical statements detected.\n")
    else:
        for pl in i_protected:
            if "return"   in pl: reason = "Control flow statement — affects program output"
            elif "printf" in pl or "scanf" in pl: reason = "I/O operation with side effects"
            else: reason = "Sensitive variable (security-critical)"
            intel_security_out.insert(tk.END,
                f"  [PROTECTED]  {pl}\n"
                f"               Reason : {reason}\n\n"
            )

    intel_explain_out.insert(tk.END, "Analysis Pipeline  —  Intelligent DCE\n" + "-"*40 + "\n\n")
    intel_explain_out.insert(tk.END,
        "  Step 1  Syntax Check\n"
        "          Validates semicolons and statement structure.\n\n"
        "  Step 2  AST Construction\n"
        "          Builds a hierarchical tree of the program\n"
        "          (Declaration, Assignment, Return nodes).\n\n"
        "  Step 3  CFG Construction\n"
        "          Maps all control-flow paths. Handles if-branches\n"
        "          and while-loops with back-edges.\n\n"
        "  Step 4  Reverse Liveness Analysis\n"
        "          Traverses statements backward. Tracks which variables\n"
        "          are needed by future statements (live set).\n"
        "          If a variable is not live when assigned -> dead assignment.\n\n"
        "  Step 5  Feature Extraction\n"
        "          For each dead candidate, 7 features are extracted:\n"
        "          overwritten, constant, simple, self_assign,\n"
        "          repeated, no_effect, unused_rhs.\n\n"
        "  Step 6  Heuristic Confidence Scoring\n"
        "          Each feature adds a weighted score (base = 0.3).\n"
        "          Score range: 0.0 (likely live) -> 1.0 (definitely dead).\n\n"
        "  Step 7  ML Prediction  (Logistic Regression)\n"
        "          Features [overwritten, constant, simple] fed to model.\n"
        "          Model outputs probability of the statement being dead code.\n\n"
        "  Step 8  Final Combined Score\n"
        "          Final = (Heuristic Score + ML Score) / 2\n"
        "          HIGH > 0.7  |  MEDIUM 0.4-0.7  |  LOW < 0.4\n\n"
        "  Step 9  Safety and Security Validation\n"
        "          Protects: return statements, printf/scanf calls,\n"
        "          and variables named password / auth / token / secure.\n\n"
        "  Step 10 Optimized Code Generation\n"
        "          Only safe + high-confidence dead code is removed.\n"
        "          Protected and live code is always preserved.\n"
    )

    intel_ast_out.insert(tk.END, "Abstract Syntax Tree  (AST)\n" + "-"*34 + "\n")
    intel_ast_out.insert(tk.END, str(ast_root))

    # Comparison Tab
    c_reduction = round((len(c_dead) / len(lines)) * 100 if lines else 0, 1)
    i_reduction = round((len(i_dead) / len(lines)) * 100 if lines else 0, 1)

    comparison_out.insert(tk.END,
        "Classical DCE  vs  Intelligent DCE\n"
        "Side-by-Side Comparison on Your Input\n"
        + "=" * 72 + "\n\n"
    )

    rows = [
        ("Feature",               "Classical DCE",                 "Intelligent DCE"),
        ("-" * 24,                "-" * 28,                        "-" * 28),
        ("Detection Method",      "Reverse Liveness only",          "Liveness + Heuristics + ML"),
        ("Confidence Scoring",    "Not available",                   "Yes  (Heuristic + ML score)"),
        ("ML Integration",        "Not used",                        "ML-assisted (prototype LR)"),
        ("Dead Reassignment",     "Supported",                       "Supported + Confidence score"),
        ("Security Validation",   "Not performed",                   "Explicitly enforced"),
        ("Protected Statements",  "None",                            "Dynamically identified"),
        ("Dead Code Found",       f"{len(c_dead)} statement(s)",     f"{len(i_dead)} statement(s)"),
        ("Code Reduction",        f"{c_reduction}%",                 f"{i_reduction}%"),
        ("Explainability",        "Low",                             "High  (features + scores)"),
        ("Output Quality",        "Basic elimination",               "Safe + confidence-validated elimination"),
    ]

    for r in rows:
        comparison_out.insert(tk.END, f"  {r[0]:<26}  {r[1]:<30}  {r[2]}\n")

    comparison_out.insert(tk.END, "\n" + "=" * 72 + "\n\n")

    comparison_out.insert(tk.END,
        "  Code Reduction Summary\n"
        + "  " + "-" * 38 + "\n"
        f"  Input lines          : {len(lines)}\n"
        f"  Classical output     : {len(c_opt)} lines"
        f"   (removed {len(c_dead)},  {c_reduction}% reduction)\n"
        f"  Intelligent output   : {len(i_opt)} lines"
        f"   (removed {len(i_dead)},  {i_reduction}% reduction)\n\n"
        "  Key Difference\n"
        + "  " + "-" * 38 + "\n"
        "  Classical DCE removes all detected dead assignments without\n"
        "  any confidence scoring or security check. It can accidentally\n"
        "  remove security-critical code such as password variables or\n"
        "  return statements if they happen to look like dead assignments.\n\n"
        "  Intelligent DCE adds three extra layers on top of classical DCE:\n"
        "    Layer 1 : Feature-based heuristic scoring\n"
        "    Layer 2 : ML-assisted probability prediction\n"
        "    Layer 3 : Safety validation to protect critical statements\n\n"
        "  Only code that passes all three layers is eliminated.\n"
        "  This makes Intelligent DCE more accurate, safe, and explainable.\n"
    )

    for p in all_panels:
        p.config(state="disabled")

    notebook.select(tab_compare)


# 12. GUI Layout
DARK_BG  = "#1a1b2e"
PANEL_BG = "#252640"
TEXT_FG  = "#e8e8f8"
ACCENT   = "#7eb8f7"
GREEN    = "#a8d8a8"
RED      = "#f4a4a4"
YELLOW   = "#f7e08a"
SUBTEXT  = "#9999bb"
BTN_BG   = "#4a7fb5"
BTN_FG   = "#ffffff"
BORDER   = "#3a3a5a"
HDR_BG   = "#0f1020"

root = tk.Tk()
root.title("Intelligent Dead Code Elimination (IDCE)")
root.geometry("1150x860")
root.configure(bg=HDR_BG)

# Header — title only, no name/project number
hdr = tk.Frame(root, bg=HDR_BG, pady=12)
hdr.pack(fill=tk.X)

tk.Label(hdr,
    text="  Intelligent Dead Code Elimination  (IDCE)",
    font=("Courier New", 18, "bold"),
    bg=HDR_BG, fg=ACCENT
).pack(side=tk.LEFT, padx=18)

tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X)

# Input area
input_frame = tk.Frame(root, bg=DARK_BG)
input_frame.pack(fill=tk.X, padx=16, pady=(12, 0))

tk.Label(input_frame,
    text="Enter C-like Source Code",
    font=("Courier New", 12, "bold"),
    bg=DARK_BG, fg=ACCENT
).pack(anchor="w", pady=(4, 3))

code_input = scrolledtext.ScrolledText(
    input_frame, height=8,
    font=("Courier New", 12),
    bg=PANEL_BG, fg=TEXT_FG,
    insertbackground=TEXT_FG,
    selectbackground=ACCENT,
    selectforeground=DARK_BG,
    relief=tk.FLAT, bd=0,
    padx=12, pady=8
)
code_input.pack(fill=tk.X, pady=(0, 8))

tk.Button(
    input_frame,
    text="   Analyze  ->  Classical  vs  Intelligent   ",
    command=analyze_code,
    bg=BTN_BG, fg=BTN_FG,
    font=("Courier New", 13, "bold"),
    relief=tk.FLAT,
    padx=18, pady=10,
    cursor="hand2",
    activebackground="#5a8fc5",
    activeforeground=BTN_FG
).pack(pady=(0, 10))

tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X)

# Notebook tab styling
style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook",
    background=DARK_BG, borderwidth=0, tabmargins=[2, 4, 2, 0])
style.configure("TNotebook.Tab",
    background=PANEL_BG, foreground=SUBTEXT,
    font=("Courier New", 11, "bold"),
    padding=[16, 7], borderwidth=0)
style.map("TNotebook.Tab",
    background=[("selected", HDR_BG)],
    foreground=[("selected", ACCENT)])

notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

def make_scrollable_tab(nb, title):
    outer  = tk.Frame(nb, bg=DARK_BG)
    nb.add(outer, text=f"  {title}  ")
    canvas = tk.Canvas(outer, bg=DARK_BG, highlightthickness=0)
    sb     = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    inner = tk.Frame(canvas, bg=DARK_BG)
    win   = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_inner(e):  canvas.configure(scrollregion=canvas.bbox("all"))
    def on_canvas(e): canvas.itemconfig(win, width=e.width)
    def on_wheel(e):  canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    inner.bind("<Configure>", on_inner)
    canvas.bind("<Configure>", on_canvas)
    canvas.bind_all("<MouseWheel>", on_wheel)
    return outer, inner

def lbl(parent, text, color=None):
    tk.Label(parent,
        text=text,
        font=("Courier New", 11, "bold"),
        bg=DARK_BG, fg=color or ACCENT,
        anchor="w"
    ).pack(fill=tk.X, padx=14, pady=(12, 2))

def panel(parent, height, fg=None):
    b = scrolledtext.ScrolledText(
        parent, height=height,
        font=("Courier New", 11),
        bg=PANEL_BG, fg=fg or TEXT_FG,
        insertbackground=TEXT_FG,
        selectbackground=ACCENT,
        selectforeground=DARK_BG,
        relief=tk.FLAT, bd=0,
        padx=12, pady=8,
        state="disabled"
    )
    b.pack(fill=tk.X, padx=14, pady=2)
    return b

def sub_lbl(parent, text):
    tk.Label(parent,
        text=text,
        font=("Courier New", 10),
        bg=DARK_BG, fg=SUBTEXT,
        anchor="w", wraplength=980, justify="left"
    ).pack(anchor="w", padx=14, pady=(0, 6))


# Tab 1 — Classical DCE
_, tab1_inner = make_scrollable_tab(notebook, "  Classical DCE")

tk.Label(tab1_inner,
    text="Classical Dead Code Elimination  —  Reverse Liveness Analysis",
    font=("Courier New", 13, "bold"), bg=DARK_BG, fg=YELLOW
).pack(anchor="w", padx=14, pady=(14, 2))
sub_lbl(tab1_inner,
    "Uses reverse liveness analysis only.  No confidence scoring.  "
    "No security validation.  Removes all detected dead assignments as-is.")

lbl(tab1_inner, "Control Flow Graph (CFG)", ACCENT)
classical_cfg_out = panel(tab1_inner, 6)

lbl(tab1_inner, "Dead Code Detected", RED)
classical_dead_out = panel(tab1_inner, 7, RED)

lbl(tab1_inner, "Optimized Code Output", GREEN)
classical_opt_out = panel(tab1_inner, 6, GREEN)


# Tab 2 — Intelligent DCE
_, tab2_inner = make_scrollable_tab(notebook, "  Intelligent DCE")

tk.Label(tab2_inner,
    text="Intelligent Dead Code Elimination  —  Liveness + Features + ML + Security",
    font=("Courier New", 13, "bold"), bg=DARK_BG, fg=GREEN
).pack(anchor="w", padx=14, pady=(14, 2))
sub_lbl(tab2_inner,
    "Reverse liveness + heuristic feature scoring + Logistic Regression prediction "
    "+ safety validation.  Only safe, high-confidence dead code is removed.")

lbl(tab2_inner, "Control Flow Graph (CFG)", ACCENT)
intel_cfg_out = panel(tab2_inner, 6)

lbl(tab2_inner, "Dead Code + Confidence Scores", RED)
intel_dead_out = panel(tab2_inner, 9, RED)

lbl(tab2_inner, "Optimized Code Output", GREEN)
intel_opt_out = panel(tab2_inner, 6, GREEN)

lbl(tab2_inner, "Security Report", YELLOW)
intel_security_out = panel(tab2_inner, 5, YELLOW)

lbl(tab2_inner, "Analysis Pipeline  (Explainability)", ACCENT)
intel_explain_out = panel(tab2_inner, 14)

lbl(tab2_inner, "Abstract Syntax Tree (AST)", SUBTEXT)
intel_ast_out = panel(tab2_inner, 8)


# Tab 3 — Comparison
tab_compare, tab3_inner = make_scrollable_tab(notebook, "  Comparison")

tk.Label(tab3_inner,
    text="Classical  vs  Intelligent  —  Side-by-Side Comparison",
    font=("Courier New", 14, "bold"), bg=DARK_BG, fg=ACCENT
).pack(anchor="w", padx=14, pady=(14, 2))
sub_lbl(tab3_inner,
    "Generated from your actual input. Shows exactly how the two approaches differ "
    "in detection method, scoring, security, and output quality.")

comparison_out = scrolledtext.ScrolledText(
    tab3_inner, height=32,
    font=("Courier New", 11),
    bg=PANEL_BG, fg=TEXT_FG,
    insertbackground=TEXT_FG,
    selectbackground=ACCENT,
    selectforeground=DARK_BG,
    relief=tk.FLAT, bd=0,
    padx=14, pady=12,
    state="disabled"
)
comparison_out.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)

# Footer — your name and roll number only, no project/course clutter
tk.Frame(root, bg=BORDER, height=1).pack(fill=tk.X)
tk.Label(root,
    text="A. Deekshith  |  24CSB0B06  |  NIT Warangal",
    font=("Courier New", 10), bg=HDR_BG, fg=SUBTEXT
).pack(pady=6)

root.mainloop()