#!/usr/bin/env python3

# Manual debugging script to check column parsing
test_row = "| 10 |<span data-tooltip=\"Interpretor.3091\">Interpretor</span> | {{Spellbreaker}} Spe | 2376| 5,045,760| 5,038,218| 3,267| 3,163| 104| 80.40%| 4,340,093| 41.10%| 64.30%| 1.20%| 22| 299| 231| 21| 323| 22| 32| 470,495| 850,428| 1| 2.32| 0| 0|"

print("Raw row:", test_row)
print()

# Split by |
cells = [cell.strip() for cell in test_row.split('|') if cell.strip()]

print("Number of cells:", len(cells))
print()

for i, cell in enumerate(cells):
    print(f"Column {i}: '{cell}'")

print()
print("Column 21 (downContribution):", cells[21] if len(cells) > 21 else "NOT FOUND")

# Test parsing logic
if len(cells) > 21:
    down_contribution_str = cells[21].replace(',', '')
    print(f"After removing commas: '{down_contribution_str}'")
    print(f"Is digit? {down_contribution_str.isdigit()}")
    
    if down_contribution_str.isdigit():
        down_contribution = int(down_contribution_str)
        print(f"Parsed value: {down_contribution}")
    else:
        print("Could not parse as integer")