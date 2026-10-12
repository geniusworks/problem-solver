import sys
from typing import Dict, List, Tuple, Optional

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0
    
    # Split into two sections by blank line
    sections = content.strip().split('\n\n')
    
    initial_values: Dict[str, int] = {}
    gates: List[Tuple[str, str, str, str]] = []  # (input1, gate_type, input2, output)
    
    # Parse first section: initial values
    if sections:
        for line in sections[0].strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                wire, value = line.split(':')
                wire = wire.strip()
                value = value.strip()
                initial_values[wire] = int(value)
    
    # Parse second section: gates
    if len(sections) > 1:
        for line in sections[1].strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Format: "input1 GATE input2 -> output"
            if '->' in line:
                left, right = line.split('->')
                right = right.strip()
                left = left.strip()
                parts = left.split()
                if len(parts) == 3:
                    input1 = parts[0]
                    gate_type = parts[1]
                    input2 = parts[2]
                    gates.append((input1, gate_type, input2, right))
    
    # Simulate the circuit using topological approach
    # Since there are no loops, we can repeatedly evaluate gates until all are resolved
    # Or we can use a simpler approach: keep a dictionary of known values and iteratively resolve
    
    wire_values: Dict[str, int] = dict(initial_values)
    unresolved_gates = list(gates)
    
    # Iteratively resolve gates
    while unresolved_gates:
        progress = False
        remaining_gates = []
        for gate in unresolved_gates:
            input1, gate_type, input2, output = gate
            if input1 in wire_values and input2 in wire_values:
                a = wire_values[input1]
                b = wire_values[input2]
                if gate_type == 'AND':
                    result = a & b
                elif gate_type == 'OR':
                    result = a | b
                elif gate_type == 'XOR':
                    result = a ^ b
                else:
                    result = 0
                wire_values[output] = result
                progress = True
            else:
                remaining_gates.append(gate)
        
        unresolved_gates = remaining_gates
        if not progress:
            # If no progress was made, but there are still unresolved gates,
            # this means we have a circular dependency or missing input
            # According to the problem, there are no loops, so this shouldn't happen
            # For safety, break to avoid infinite loop
            break
    
    # Collect all z-wires and compute the decimal number
    z_wires = []
    for wire in wire_values:
        if wire.startswith('z'):
            # Extract the number part
            z_num_str = wire[1:]
            try:
                z_num = int(z_num_str)
                z_wires.append((z_num, wire_values[wire]))
            except ValueError:
                pass
    
    # Sort by z number
    z_wires.sort(key=lambda x: x[0])
    
    # Compute the decimal number
    # z00 is least significant bit (bit 0), z01 is bit 1, etc.
    result = 0
    for i, (z_num, value) in enumerate(z_wires):
        if z_num == i:
            result |= (value << z_num)
        else:
            # If z numbers are not contiguous, handle by position
            result |= (value << z_num)
    
    return result

if __name__ == '__main__':
    print(solve())