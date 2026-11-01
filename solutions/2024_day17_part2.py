from typing import List


def solve() -> int:
    with open('input.txt', 'r') as f:
        lines = f.readlines()
    
    # Parse registers and program
    register_a = 0
    register_b = 0
    register_c = 0
    program = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('Register A:'):
            register_a = int(line.split(': ')[1])
        elif line.startswith('Register B:'):
            register_b = int(line.split(': ')[1])
        elif line.startswith('Register C:'):
            register_c = int(line.split(': ')[1])
        elif line.startswith('Program:'):
            program_str = line.split(': ')[1]
            program = [int(x) for x in program_str.split(',')]
    
    # The program should output a copy of itself
    # So the expected output is the program itself
    expected_output = program
    
    # We need to find the lowest positive value of A such that
    # running the program with B=0, C=0 produces exactly expected_output
    
    # Let's implement the computer simulation
    def run_program(a_val: int, b_val: int, c_val: int, prog: List[int]) -> List[int]:
        a = a_val
        b = b_val
        c = c_val
        ip = 0
        output_values = []
        
        def get_combo_value(operand: int) -> int:
            if operand <= 3:
                return operand
            elif operand == 4:
                return a
            elif operand == 5:
                return b
            elif operand == 6:
                return c
            else:
                raise ValueError(f"Invalid combo operand: {operand}")
        
        while ip < len(prog):
            opcode = prog[ip]
            operand = prog[ip + 1] if ip + 1 < len(prog) else None
            
            if opcode == 0:  # adv
                combo_val = get_combo_value(operand)
                a = a // (2 ** combo_val)
            elif opcode == 1:  # bxl
                b = b ^ operand
            elif opcode == 2:  # bst
                combo_val = get_combo_value(operand)
                b = combo_val % 8
            elif opcode == 3:  # jnz
                if a != 0:
                    ip = operand
                    continue
            elif opcode == 4:  # bxc
                b = b ^ c
            elif opcode == 5:  # out
                combo_val = get_combo_value(operand)
                output_values.append(combo_val % 8)
            elif opcode == 6:  # bdv
                combo_val = get_combo_value(operand)
                b = a // (2 ** combo_val)
            elif opcode == 7:  # cdv
                combo_val = get_combo_value(operand)
                c = a // (2 ** combo_val)
            
            ip += 2
        
        return output_values
    
    # The program is: 2,4,1,3,7,5,4,2,0,3,1,5,5,5,3,0
    # Let's analyze the structure:
    # ip=0: bst 4 -> B = A % 8
    # ip=2: bxl 3 -> B = B ^ 3
    # ip=4: cdv 5 -> C = A // (2 ** B)
    # ip=6: bxc 2 -> B = B ^ C
    # ip=8: adv 3 -> A = A // 8
    # ip=10: bxl 5 -> B = B ^ 5
    # ip=12: out 5 -> output B % 8
    # ip=14: jnz 0 -> if A != 0, jump to 0
    
    # So each iteration:
    # 1. B = A % 8
    # 2. B = B ^ 3
    # 3. C = A // (2 ** B)
    # 4. B = B ^ C
    # 5. A = A // 8
    # 6. B = B ^ 5
    # 7. output B % 8
    # 8. if A != 0, loop; else halt
    
    # The number of iterations equals the number of times we can divide A by 8 and still have a non-zero result
    # This is ceil(log8(A)) = number of 3-bit groups in A
    
    # The expected output has len(expected_output) values
    # So we need exactly len(expected_output) iterations
    
    # Let's brute force from 1 upwards until we find a match
    # But A could be very large. Let's think about this differently.
    
    # Actually, let's just brute force. The answer for the example was 117440, which is not too large.
    # For this problem, the program is 16 values long, so A should produce 16 outputs.
    # 8^15 <= A < 8^16, so A is between 3.5e13 and 2.8e14. That's too large to brute force naively.
    
    # Let's work backwards from the last output.
    # Let outputs be o[0], o[1], ..., o[n-1] where n = len(expected_output)
    # Let A_0 = A, A_1 = A // 8, ..., A_{n-1} = A // 8^(n-1)
    # The last output o[n-1] is produced when A_{n-1} is the current value of A.
    # After outputting, A becomes A_{n-1} // 8. For the loop to terminate, A_{n-1} // 8 must be 0.
    # So A_{n-1} is between 1 and 7.
    
    # Let's define the transformation for one iteration:
    # Given A_k, B_k, C_k (state before iteration k)
    # B_temp = A_k % 8
    # B_temp = B_temp ^ 3
    # C_temp = A_k // (2 ** B_temp)
    # B_temp = B_temp ^ C_temp
    # A_{k+1} = A_k // 8
    # B_temp = B_temp ^ 5
    # output = B_temp % 8
    
    # Note that B and C from previous iterations don't seem to carry over in a simple way
    # because B is overwritten each time, and C is overwritten each time.
    # Let's verify:
    # - B is set to A % 8, so previous B is irrelevant.
    # - C is set to A // (2 ** B), so previous C is irrelevant.
    # So the only state that carries over is A.
    
    # Therefore, given A_k, the output is fully determined.
    # Let f(A_k) = output value when starting with A_k (and B=0, C=0, but they get overwritten)
    
    # We need:
    # f(A) = expected_output[0]
    # f(A // 8) = expected_output[1]
    # ...
    # f(A // 8^(n-1)) = expected_output[n-1]
    # And A // 8^n = 0
    
    # Let's define f(x) for x > 0:
    # b = x % 8
    # b = b ^ 3
    # c = x // (2 ** b)
    # b = b ^ c
    # b = b ^ 5
    # return b % 8
    
    # We need to find the smallest A such that this sequence of constraints is satisfied.
    
    # We can work backwards.
    # Let A_{n-1} be the value such that f(A_{n-1}) = expected_output[n-1] and A_{n-1} < 8.
    # Then A_{n-2} must satisfy:
    #   A_{n-2} // 8 = A_{n-1}  =>  A_{n-2} is in [8 * A_{n-1}, 8 * A_{n-1} + 7]
    #   f(A_{n-2}) = expected_output[n-2]
    
    # So for each level, we have a range of possible values for A_k, and we need to find
    # which ones in that range produce the correct output.
    
    # Let's implement this.
    
    n = len(expected_output)
    
    # Start with the last iteration
    # A_{n-1} must be in [1, 7] (since it must be non-zero for the iteration to happen, and < 8 for the next to be 0)
    # Actually, A_{n-1} can be 0? No, because if A_{n-1} = 0, the jnz would not jump, but the output would still happen.
    # Wait, let's re-read:
    # ip=14: jnz 0 -> if A != 0, jump to 0.
    # The output happens at ip=12, before the jnz.
    # So even if A becomes 0 after the adv instruction, the output still happens.
    # But the condition for the loop to continue is A != 0 after the adv.
    # So A_{n-1} // 8 must be 0, which means A_{n-1} < 8.
    # And A_{n-1} can be 0? If A_{n-1} = 0, then f(0) would be computed.
    # Let's check f(0):
    # b = 0 % 8 = 0
    # b = 0 ^ 3 = 3
    # c = 0 // (2 ** 3) = 0
    # b = 3 ^ 0 = 3
    # b = 3 ^ 5 = 6
    # output = 6 % 8 = 6
    # So f(0) = 6.
    # But if A_{n-1} = 0, then the previous value A_{n-2} // 8 = 0, so A_{n-2} < 8.
    # And the iteration with A_{n-2} would have A_{n-2} // 8 = 0, so A_{n-1} = 0.
    # This is consistent.
    # However, for the loop to have exactly n iterations, we need:
    # A // 8^(n-1) >= 1 (so that the n-th iteration happens with A_{n-1} >= 1? No, A_{n-1} can be 0)
    # Actually, the loop continues as long as A != 0 after the adv.
    # So for iteration i (0-indexed), we need A_i != 0 at the start? No.
    # Let's trace carefully:
    # At the start of an iteration, A is some value.
    # After adv, A becomes A // 8.
    # Then jnz checks if A (the new value) is non-zero.
    # So the condition to continue is (A_old // 8) != 0, i.e., A_old >= 8.
    # So for the last iteration (iteration n-1), we need A_{n-1} < 8 (so that A_{n-1} // 8 = 0 and the loop terminates).
    # And for all previous iterations i < n-1, we need A_i >= 8.
    
    # So:
    # A_{n-1} is in [0, 7]
    # A_{n-2} is in [8, 63] (since A_{n-2} // 8 = A_{n-1}, so A_{n-2} in [8*A_{n-1}, 8*A_{n-1}+7], and A_{n-2} >= 8)
    # ...
    # A_0 = A is in [8^(n-1), 8^n - 1]
    
    # Let's find all possible values for A_{n-1} in [0, 7] that produce expected_output[n-1].
    # Then for each, find all possible A_{n-2} in [8*A_{n-1}, 8*A_{n-1}+7] that produce expected_output[n-2] and are >= 8.
    # And so on.
    
    # We want the smallest A_0.
    
    # Let's implement this backtracking.
    
    def compute_output(a_val: int) -> int:
        b = a_val % 8
        b = b ^ 3
        c = a_val // (2 ** b)
        b = b ^ c
        b = b ^ 5
        return b % 8
    
    # Work backwards from the last output
    # possible_values is a list of possible values for A_k
    # Start with k = n-1
    possible_values = []
    
    # For the last iteration, A_{n-1} can be 0 to 7
    for val in range(0, 8):
        if compute_output(val) == expected_output[n-1]:
            possible_values.append(val)
    
    # Now work backwards from n-2 to 0
    for k in range(n-2, -1, -1):
        new_possible_values = []
        for val in possible_values:
            # A_k must be such that A_k // 8 = val
            # So A_k is in [8*val, 8*val + 7]
            # And A_k must be >= 8 (unless k == 0, but even then, if n > 1, A_0 must be >= 8^(n-1) >= 8)
            start = 8 * val
            end = 8 * val + 8
            for candidate in range(start, end):
                # For k > 0, we need candidate >= 8
                # For k == 0, we need candidate >= 1 (positive)
                if k > 0 and candidate < 8:
                    continue
                if k == 0 and candidate < 1:
                    continue
                if compute_output(candidate) == expected_output[k]:
                    new_possible_values.append(candidate)
        possible_values = new_possible_values
    
    # The answer is the smallest value in possible_values (which corresponds to A_0)
    if possible_values:
        return min(possible_values)
    else:
        # Fallback to brute force (should not happen)
        for a_val in range(1, 10**15):
            if run_program(a_val, 0, 0, program) == expected_output:
                return a_val
        return -1


if __name__ == '__main__':
    print(solve())