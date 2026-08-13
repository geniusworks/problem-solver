import sys
from typing import List, Dict, Tuple

def solve() -> int:
    # Read all lines from input.txt
    try:
        with open('input.txt', 'r') as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        print("Error: input.txt not found.")
        sys.exit(1)

    if not raw_lines:
        return 0
    
    # Filter out empty lines and strip whitespace to ensure clean processing
    lines = [line.strip() for line in raw_lines]
    
    # Split into Rules section (top) and Updates section (bottom) using a blank line as delimiter
    update_index = -1
    rule_section = []
    updates_list = []

    if len(lines) > 0:
        # Find the first empty line to separate rules from updates. 
        # If there is no empty line, treat everything above (or all) based on format hints.
        for i in range(len(lines)):
            if not lines[i]:  # Empty string after strip means blank line
                update_index = i
                break
        
    if update_index == -1:
        # If the delimiter is missing but we have a standard AoC Day 5 structure, 
        # usually it's just one block of updates or rules. However, based on the problem description, 
        # there are two distinct sections separated by an empty line in examples. 
        # We will assume if no blank line exists and lines exist, they might be mixed or we handle simply.
        # But strictly following "Section A... Section B" implies a separator.
        # If the input doesn't have a blank line separating them (e.g. just rules then updates immediately), 
        # it's ambiguous without more context. However, standard AoC inputs always have this blank line.
        pass

    # Process Rules section: lines from 0 to update_index - 1 (if separator exists)
    if update_index != -1 and update_index > 0:
        rule_section = lines[:update_index]
        
        # Parse rules into a dictionary mapping 'A' -> set of pages that must come after A
        page_rules: Dict[int, set] = {}
        
        for line in rule_section:
            if not line or '|' not in line:
                continue
            
            parts = line.split('|')
            try:
                x = int(parts[0].strip())
                y = int(parts[1].strip())
                
                # Rule X|Y means X must be printed before Y. 
                # Store as dependency graph edges or simply a rule set to validate later.
                if x not in page_rules:
                    page_rules[x] = set()
                page_rules[x].add(y)
            except ValueError:
                continue

    else:
        # If no separator is found, we might have only one section (Updates?) or the input format differs slightly.
        # Given the problem description explicitly mentions two sections separated by a blank line in examples, 
        # if that delimiter isn't present, it's safer to assume either there are no rules provided for this run
        # or the whole file is updates (unlikely given "Example 1" structure).
        # We will proceed with whatever we can parse. If update_index == -1 and len > 0:
        rule_section = [] 
        # In a real scenario, if there's no blank line separating rules from updates in standard format, 
        # it might be that the input is malformed or I'm misinterpreting "blank line". 
        # However, let's assume strict adherence to finding an empty line.
        
    # Process Updates section: lines starting at update_index + 1 (or if no separator found)
    
    start_idx = update_index + 1 if update_index != -1 else len(lines)
    
    updates_list = []
    for i in range(start_idx, len(lines)):
        line = lines[i]
        # Skip empty lines within the updates section just in case (though usually none exist between valid entries except separator)
        if not line: 
            continue
        
        try:
            parts_str = line.split(',')
            update_pages = [int(x.strip()) for x in parts_str]
            
            # Only add non-empty lists of pages to our validation list
            if len(update_pages) > 0:
                updates_list.append(update_pages)

        except ValueError:
            continue
            
    total_middle_sum = 0
    
    for update_sequence in updates_list:
        current_order_map: Dict[int, int] = {} # Map page -> index (position) in this specific update
        
        try:
            for idx, page_val in enumerate(update_sequence):
                current_order_map[page_val] = idx
        except KeyError: 
            continue
            
        is_valid_update = True
        
        # Check rules against the filtered set of pages present in this update
        # For every rule X|Y where both X and Y are in 'update_sequence', check if index(X) < index(Y).
        
        for x, y_set in page_rules.items():
            if x not in current_order_map:
                continue
            
            for y in y_set:
                if y not in current_order_map:
                    # Rule involves a missing page Y. According to problem description: 
                    # "ordering rules that involve missing page numbers are ignored" -> Ignore this rule check?
                    # Wait, the logic is: If X and Y are *both* produced (present), then order matters.
                    # So if y is not in current_order_map, we ignore this specific constraint for now? 
                    # Or does it mean "If both page number X and page number Y are to be produced...". Yes.
                    continue
                
                # Both present. Check order.
                if current_order_map[x] >= current_order_map[y]:
                    is_valid_update = False
                    break
            
            if not is_valid_update:
                break
        
        if is_valid_update:
            n_pages = len(update_sequence)
            
            # Calculate middle index (0-indexed, integer division of length-1 by 2 for odd lengths?) 
            # Example: Length 5 -> Middle at index 2. Formula: (N - 1) // 2? 
            # Let's re-read carefully: "75,47,61,53,29" -> N=5. Middle is '61' which is the 3rd item.
            # Indexes: 0->75, 1->47, 2->61, 3->53, 4->29. 
            # (5-1)//2 = 2. Correct.
            
            middle_idx = (n_pages - 1) // 2
            
            if n_pages > 0:
                total_middle_sum += update_sequence[middle_idx]

    return total_middle_sum

if __name__ == "__main__":
    import sys, inspect
    sig = inspect.signature(solve)
    params = len(sig.parameters)
    if params == 0:
        print(solve())
    elif params == 1:
        arg = sys.argv[1] if len(sys.argv) > 1 else "input.txt"
        print(solve(arg))
    else:
        raise TypeError("solve() must take 0 or 1 arguments")