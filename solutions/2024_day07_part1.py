def solve():
    try:
        with open('input.txt') as f:
            content = f.read().strip()
        
        if not content:
            return 0
            
        total_sum = 0
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Parse target and numbers. Format is "TARGET : NUM1 NUM2 ..." or similar variations with spaces?
            # The provided example lines have NO operators in the input string, just space-separated numbers after colon. 
            # Wait! Looking at standard Advent of Code Day 7 inputs: they often contain `Target : Num Op Num`? No, usually it's `Num1 + Num2`.
            
            # Let me re-read the problem text provided by user VERY carefully regarding input format again.
            # "For example: ... 190: 10 19" -> The line shows numbers separated by spaces only. 
            # However, standard AoC Day 7 inputs are like `Target : Num Op Num`? Or just `Num`s with space delimiters and we fill ops.
            
            # Wait! There is a crucial detail: "Input Format Analysis".
            # If the input lines contain NO operators (just spaces), then my logic of parsing numbers works perfectly. 
            # But what if they DO contain operators? e.g., `Target : A + B`.
            # The problem statement says: "some young elephants were playing nearby and stole all the operators from their calibration equations!"
            # This implies the original equation had them, but now we have to determine which test values could possibly be produced by placing ANY combination. 
            # It strongly suggests that in the *input file*, only numbers are present (separated by spaces), or maybe they are separated by something else? 
            
            # Let's look at standard AoC Day 7 examples online:
            # Example input line: "190 : 10 19". Wait, usually there is a space after colon. 
            # Is it possible the input contains operators like `+` and `*` already? No, because we are supposed to determine which ones work by placing ANY combination.
            # If they were already placed in the file (like "81 + 40"), then there would be no need for us to try all combinations; it would just be a simple evaluation check. 
            # The fact that we have to find *a* valid configuration implies the input numbers are available slots where operators go, or perhaps they are already present as placeholders?
            
            # Actually! Reading standard Day 7 problem text: "You ask how long... engineers tell you it needs final calibrations but some young elephants stole all the operators from their calibration equations!" 
            # This implies we need to *find* if a valid configuration exists.
            # The provided example lines in the prompt are `190: 10 19`. There is NO operator visible between 10 and 19, just spaces? Or does it mean "between 10 and 19"? 
            # It seems likely that the input file provides numbers separated by spaces ONLY. We must insert + or *.
            
            # HOWEVER! Let's look at a specific edge case: `3267: 81 40 27`. If there were operators, it would be something like `81 + 40 * 27`? 
            # But the problem says "stealed all the operators". So we must insert them.
            
            pass

    except FileNotFoundError:
        return 0
        
def solve():
    try:
        with open('input.txt') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        total_sum = 0
        
        for raw_line in lines:
            # Parse the target and numbers. 
            # The format is usually `Target : Num1 Num2 ...`. Sometimes there might be spaces around colon?
            # Let's handle both cases robustly by splitting on ':' first.
            
            if ':' not in raw_line:
                continue
                
            parts = raw_line.split(':', 1)
            target_str = parts[0].strip()
            rest_part = parts[1]
            
            try:
                target_val = int(target_str)
            except ValueError:
                # Skip lines with invalid targets (though unlikely per problem spec)
                continue
                
            # Parse the numbers from 'rest_part'. 
            # It might look like " 81 + 40 * 27" or just "81 40 27".
            # If operators are present in input, we should probably ignore them and treat adjacent tokens as operands?
            # But standard AoC Day 7 inputs usually have numbers separated by spaces ONLY. 
            # Wait! Let's re-read the prompt text again. "For example: ... 190: 10 19". There are no operators in this string representation provided.
            # However, is it possible that '81 + 40' appears? No, because elephants stole them. 
            # So the input must be `Num`s separated by spaces (or maybe just raw strings?).
            
            tokens = rest_part.split()
            if not tokens:
                continue
            
            try:
                numbers = [int(token) for token in tokens]
            except ValueError:
                continue
                
            count_nums = len(numbers)
            if count_nums == 0:
                continue
                
            # If there are operators in the input (unlikely given "stole all operators"), we would need to handle them. 
            # Given the logic of the puzzle ("determine which test values could possibly be produced by placing any combination..."),
            # it implies brute forcing + and * over n-1 slots.
            
            num_slots = count_nums - 1
            
            if num_slots <= 0:
                continue
                
            found_any_valid_config = False
            
            # Iterate through all possible operator assignments (2^(n-1))
            for i in range(1 << num_slots):
                current_result = numbers[0]
                
                valid_combo_found_for_this_i = True
                
                # Evaluate left-to-right. 
                # Loop over slots from 0 to n-2. Slot j is between result of (j) and number(j+1).
                for slot_idx in range(num_slots):
                    next_num_index = slot_idx + 1
                    operator_choice_bit = (i >> slot_idx) & 1
                    
                    # Determine operation based on bit: 
                    # Let's say 0 is '+', 1 is '*'. Order doesn't strictly matter as long as we cover all.
                    
                    if operator_choice_bit == 0:
                        current_result += numbers[next_num_index]
                    else:
                        current_result *= numbers[next_num_index]
                
                if current_result == target_val:
                    found_any_valid_config = True
                    break # We only need one valid configuration to count the equation as "true"
            
            if found_any_valid_config:
                total_sum += target_val
                
        return total_sum

    except FileNotFoundError:
        print("Error: input.txt not found.")
        exit(1)
    except Exception as e:
        # Handle unexpected errors gracefully or just let them bubble up? 
        # Usually, we should avoid crashing. But for a coding contest solution, if logic is correct, no crash needed unless file missing.
        return 0

if __name__ == '__main__':
    print(solve())