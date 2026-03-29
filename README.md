# Intelligent Dead Code Elimination (IDCE)

A compiler optimization tool that detects and removes dead code from C-like
source programs using static analysis, machine learning, and security validation.

Built as part of the Compiler Design Mini Project (Project No. 56)
at the National Institute of Technology, Warangal.

---

## What is Dead Code?

Dead code is any statement in a program whose result is never used.

Examples:
- A variable that is assigned but never read
- A variable that is overwritten before its value is ever used
- A constant assignment that has no effect on the program output

Dead code wastes memory, reduces readability, and can hide security bugs.

---

## What This Project Does

This system takes C-like source code as input and:

1. Detects dead assignments using reverse liveness analysis
2. Scores each dead candidate using heuristic rules and a machine learning model
3. Validates safety before removing anything (protects return statements,
   I/O operations, and security-sensitive variables)
4. Generates optimized code with dead statements removed
5. Shows a side-by-side comparison of Classical DCE vs Intelligent DCE

---

## How It Is Different from Classical DCE

Classical dead code elimination just removes anything it finds using
liveness analysis alone. It has no confidence scoring and no security check.

This system adds three extra layers on top:

- Layer 1 : Feature-based heuristic confidence scoring
- Layer 2 : ML-assisted prediction using Logistic Regression
- Layer 3 : Safety validation to protect critical statements

Only code that passes all three layers is removed.

---

## Requirements

- Python 3.8 or higher
- scikit-learn library

tkinter and re are built into Python — no separate install needed.

---

## Installation

Install the only external dependency:

```
pip install scikit-learn
```

---

## How to Run

```
python idce_final.py
```

The GUI window will open. Type your C-like source code in the input box
and click the Analyze button.

---

## Supported Input Syntax

The system accepts a restricted subset of C:

```
int a = 5;
int b = a + 2;
int c = 10;
b = 20;
return b;
```

Supported statements:
- Integer variable declarations       ->  int a = 5;
- Assignment statements               ->  b = 20;
- Arithmetic expressions              ->  int b = a + 2;
- Conditional statements              ->  if (a > 0)
- While loops                         ->  while (i < 5)
- Return statements                   ->  return b;
- I/O operations                      ->  printf(a);

Not supported:
- Pointers and arrays
- Function definitions
- Preprocessor directives (#include, #define)

---

## GUI Overview

The interface has three tabs:

**Tab 1 — Classical DCE**
Shows what classical reverse liveness analysis finds and removes.
No confidence score. No security check.

**Tab 2 — Intelligent DCE**
Shows dead code with confidence scores, ML scores, and feature breakdown.
Also shows the security report and full 10-step analysis pipeline.

**Tab 3 — Comparison**
Auto-opens after analysis. Shows a side-by-side table comparing both
approaches on your actual input — detection method, scoring, security,
code reduction percentage.

---

## Example

Input:
```
int a = 5;
int b = a + 2;
int c = 10;
b = 20;
return b;
```

Output (Intelligent DCE):
```
int a = 5;
b = 20;
return b;
```

Dead code removed:
- int b = a + 2;   (overwritten before use, Final Score: 0.68)
- int c = 10;      (never used anywhere,   Final Score: 0.76)

Protected:
- return b;        (control flow statement)

---

## Security Protection

The system will never remove:

| Statement type         | Reason                            |
|------------------------|-----------------------------------|
| return statements      | Control flow — affects output     |
| printf / scanf         | I/O operations with side effects  |
| password / auth / token / secure      | Sensitive variable names          |

---

## Project Structure

```
IDCE_Project/
|
|-- idce_final.py        <- Main application (run this)
|-- README.md            <- This file
|
|-- Weekly_Reports/
    |-- Week_1  Problem Definition
    |-- Week_2  Literature Survey
    |-- Week_3  SRS
    |-- Week_4  Architecture Design
    |-- Week_5  Language and IR Design
    |-- Week_6  Frontend and AST
    |-- Week_7  CFG Construction
    |-- Week_8  Classical DCE
    |-- Week_9  Intelligent DCE
    |-- Week_10 Security and Optimization
    |-- Week_11 Testing and Validation
    |-- Week_12 Evaluation and Benchmarking
    |-- Week_13 Explainability
    |-- Week_14 Final Report and Demo
```

---

## Known Limitations

- ML model is trained on a small synthetic dataset (prototype only)
- Security detection is keyword-based, not semantic
- Does not support pointers, arrays, or function definitions
- CFG-based path-sensitive analysis is not yet implemented

---

## Author

**A. Deekshith**
Roll No: 24CSB0B06
Department of Computer Science and Engineering
National Institute of Technology, Warangal
