import sys


def solve() -> str:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return ""
    
    # Parse the input
    A = 0
    B = 0
    C = 0
    program = []
    
    for line in lines:
        if line.startswith("Register A:"):
            A = int(line.split(":")[1].strip())
        elif line.startswith("Register B:"):
            B = int(line.split(":")[1].strip())
        elif line.startswith("Register C:"):
            C = int(line.split(":")[1].strip())
        elif line.startswith("Program:"):
            prog_str = line.split(":", 1)[1].strip()
            program = [int(x) for x in prog_str.split(",")]
    
    def combo(operand: int) -> int:
        if operand < 4:
            return operand
        elif operand == 4:
            return A
        elif operand == 5:
            return B
        elif operand == 6:
            return C
        else:
            raise ValueError(f"Invalid combo operand: {operand}")
    
    ip = 0
    output = []
    
    while ip < len(program):
        if ip + 1 >= len(program):
            break
        
        opcode = program[ip]
        operand = program[ip + 1]
        
        if opcode == 0:  # adv
            denom = 2 ** combo(operand)
            A = A // denom
        elif opcode == 1:  # bxl
            B = B ^ operand
        elif opcode == 2:  # bst
            B = combo(operand) % 8
        elif opcode == 3:  # jnz
            if A != 0:
                ip = operand
                continue
        elif opcode == 4:  # bxc
            B = B ^ C
        elif opcode == 5:  # out
            output.append(combo(operand) % 8)
        elif opcode == 6:  # bdv
            denom = 2 ** combo(operand)
            B = A // denom
        elif opcode == 7:  # cdv
            denom = 2 ** combo(operand)
            C = A // denom
        
        ip += 2
    
    return ",".join(map(str, output))


if __name__ == '__main__':
    print(solve())