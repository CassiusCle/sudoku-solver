import numpy as np
import itertools
from typing import Optional, Tuple, Union
import logging

# Set up logging configuration  
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s') 

class SudokuSolver:
    """A class for solving 9x9 Sudoku puzzles.
    use NJIT numba decorator as optional for large lists
    """
    
    def __init__(self):
        """Initializes the SudokuSolver class."""
        pass

    def print_puzzle(self, puzzle: Union[str, int], solution: Optional[str] = None) -> None:
        """Prints a sudoku puzzle and its solution in a formatted way.

        Args:
            puzzle: A string or integer representing the initial sudoku puzzle.
            solution: An optional string representing the solution to the puzzle.
        """
        
        # Convert puzzle numbers to letters for readability to distinguish from solution values later
        alphabet = 'abcdefghi'
        puzzle = ''.join(
            [alphabet[int(c) - 1] if c not in ['.', '0'] else c for c in str(puzzle)]
        )
        
        # Overlay solution onto puzzle if provided
        if solution:
            puzzle = ''.join(
                [c1 if c1.isalpha() else c2 for c1, c2 in zip(puzzle, solution)]
            )

        # Helper function to divide a string into equal-sized chunks
        def chunk_string(string: str, chunk_size: int) -> list[str]:
            """Divides a string into chunks of equal size."""
            return [string[i:i + chunk_size] for i in range(0, len(string), chunk_size)]

        # Break the puzzle string into lines and 3x3 blocks
        digits_per_line: list = chunk_string(puzzle, 9)
        digits_per_line: list = [chunk_string(line, 3) for line in digits_per_line]
        
        # Define the horizontal and vertical lines for the sudoku grid
        hz_line = '─' * 9
        top_line = f'┌{hz_line}┬{hz_line}┬{hz_line}┐'
        mid_line = f'├{hz_line}┼{hz_line}┼{hz_line}┤'
        bottom_line = f'└{hz_line}┴{hz_line}┴{hz_line}┘'

        # Assemble the top line of the sudoku grid
        output = [top_line]
        for i, digits in enumerate(digits_per_line):
            # Join the 3x3 blocks with vertical lines
            output.append('│' + '│'.join(''.join(chunk) for chunk in digits) + '│')
            # Add middle lines after every third line to form grid
            if i in [2, 5]:
                output.append(mid_line)
        # Add the bottom line to complete the grid
        output.append(bottom_line)    

        # Helper function to replace characters with formatted numbers
        def replace_chars(chars: str) -> str:
            """Replaces characters in the puzzle output with formatted numbers."""
            return ''.join(
                f'({alphabet.index(c) + 1})' if c.isalpha() else ' . ' if c in ['.', '0']
                else f' {c} ' if c.isdigit() else c for c in chars
            )
        
        # Print the final formatted sudoku grid
        print('\n'.join(replace_chars(line) for line in output))
    

    def validate_solution(self, candidate_solution: np.ndarray) -> bool:
        """Check if a Sudoku solution is valid.

        Validates a 9x9x9 3D array representing a Sudoku puzzle solution, where each layer in the third dimension 
        corresponds to the positions of (n+1)s in the solution. 
        The approach for
        solution validation is based on the one outlined in a MathOverflow post
        (https://mathoverflow.net/questions/129143/verifying-the-correctness-of-a-sudoku-solution).

        Args:
            candidate_solution (np.ndarray): A 3D array representing a proposed Sudoku solution.

        Raises:
            TypeError: If candidate_solution is not a numpy.ndarray.
            ValueError: If candidate_solution does not have the correct shape or number of elements.
            ValueError: If candidate_solution does not exactly one digit for each field in the original Sudoku

        Returns:
            bool: True if the solution is valid, False otherwise.
        """
        if not isinstance(candidate_solution, np.ndarray):
            raise TypeError(f'Expected numpy.ndarray, got {type(candidate_solution).__name__}.')

        if candidate_solution.shape != (9, 9, 9):
            raise ValueError('Candidate solution must be a 9x9x9 3D array.')
        
        if not np.all(candidate_solution.sum(axis=2) == 1):
            raise ValueError('Candidate solution does not contain exactly one digit on each field.')
        
        # Check if all rows contain each digit only once (sum is over cols)
        if not np.all(candidate_solution.sum(axis=1) == 1):
            return False
        
        # Check if all cols contain each digit only once (sum is over rows)
        if not np.all(candidate_solution.sum(axis=0) == 1):
            return False

        for i in range(0, 6, 3):
            for j in range(0, 6, 3):
                if not np.all(candidate_solution[i:i+3, j:j+3].sum(axis=(0, 1)) == 1):
                    return False
    
        return True
    
    def validate_solution_list_or_string(self, candidate_solution: str | list) -> bool:
        """" Validates a candidate solution when the input is a list or string """
        _, candidate_3d = self._string_to_np_puzzle(candidate_solution)
        return self.validate_solution(candidate_solution=candidate_3d)
    

    def solve_string(self, unsolved_sudoku: str, verbose: bool = False, max_iterations = 10_000_000) -> str:
        """Solve the Sudoku puzzle.

        This method solves the Sudoku puzzle by first pruning the candidates based on filled values until no further reduction is possible.
        If only one combination is left, it returns the solution. Otherwise, it brute forces solutions.

        Args:
            unsolved_sudoku (str): The unsolved Sudoku puzzle in string format.
            verbose (bool, optional): If True, print the iteration at which the solution was found. Defaults to False.
            fill_from_top (bool, optional): If True, fill the Sudoku from top. Defaults to True.

        Returns:
            str: The solved Sudoku puzzle in string format.
        """    
        candidates_per_field = [list(range(1,10)) if i == '0' else [int(i)] for i in list(unsolved_sudoku)]

        # Prune the candidates based on filled values until no further reduction is possible
        current_combinations = self._count_combinations(candidates_per_field)
        while True:
            previous_combinations = current_combinations
            for _, idx in SudokuSolver.ROW_INDICES+SudokuSolver.COL_INDICES+SudokuSolver.SUBSQ_INDICES:
                candidates_per_field = self._prune_filled_values(idx=idx, candidates_per_field=candidates_per_field)
            
            current_combinations = self._count_combinations(candidates_per_field)
            
            if current_combinations >= previous_combinations or current_combinations == 1:
                break
        
        # Return solution in case only one combination is left (=solved)
        if current_combinations == 1:
            return ''.join([str(c[0]) for c in candidates_per_field])

        if current_combinations >= max_iterations or current_combinations < 0:
            logging.warning(f'More than {max_iterations:_} combinations to check, aborting...')
            return None
        
        # Brute force solutions        
        combinations = itertools.product(*candidates_per_field)
        i = 0
        for combination in combinations:
            i += 1
            if self.validate_solution_list_or_string(candidate_solution=list(combination)):
                break
        if verbose: print(f'Solution found at iteration: {i} of {current_combinations}')
        return ''.join([str(i) for i in combination])
    
    def _string_to_np_puzzle(self, sudoku: str) -> Tuple[np.ndarray, np.ndarray]:
        """"Convert a string representing a sudoku puzzle into the 2D puzzle and 3D possibilities representations as numpy arrays"""
        puzzle_2d: np.ndarray = np.reshape(np.array(list(sudoku), dtype=np.byte), newshape=(9, 9))
        options_3d: np.ndarray = np.zeros((9,9,9), dtype=np.byte) # [row][column][depth]
        
        # Get the indices where value is not zero
        nonzero_indices = np.nonzero(puzzle_2d)
        
        # Subtract 1 from the values at these indices because our options_3d is 0-indexed
        values = puzzle_2d[nonzero_indices] - 1
        
        # Set the corresponding positions in options_3d to 1
        options_3d[nonzero_indices[0], nonzero_indices[1], values] = 1
        
        # For zero values in puzzle_2d, set the entire depth to 1 in options_3d
        zero_indices = np.where(puzzle_2d == 0)
        options_3d[zero_indices[0], zero_indices[1]] = 1
        
        return puzzle_2d, options_3d

    def _np_puzzle_to_string(self, np_puzzle: np.ndarray) -> str:
        """converts the puzzle back into a string"""
        return ''.join(map(str, (np_puzzle.argmax(axis=2)+1).flatten()))
    
    def _unique_combinations(self, *iterables):
        """A generator function that yields the indices of the cells in the sudoku possibilities cube.
        It yields a tuple with the indices of the cells that need to be set to 1 and the indices of the previous cells that must be set to 0.
        """

        # Create an iterator for all combinations
        combinations: itertools.product = itertools.product(*iterables)
        prev_comb = None

        # Get the first combination
        comb = next(combinations)

        # For the first combination, yield all elements
        yield tuple((None, c) for c in comb)
        prev_comb = comb

        # Now the for loop will start from the second combination
        for comb in combinations:
            # Yield only elements that are different from the previous combination
            yield tuple((p, c) for c, p in zip(comb, prev_comb) if c != p)
            prev_comb = comb

    def solve(self, unsolved_sudoku: str, max_iterations: int=10_000_000) -> str:
        # """Solve the Sudoku puzzle.

        # This method solves the Sudoku puzzle by first pruning the candidates based on filled values until no further reduction is possible.
        # If only one combination is left, it returns the solution. Otherwise, it brute forces solutions.

        # Args:
        #     unsolved_sudoku (str): The unsolved Sudoku puzzle in string format.
        #     verbose (bool, optional): If True, print the iteration at which the solution was found. Defaults to False.
        #     fill_from_top (bool, optional): If True, fill the Sudoku from top. Defaults to True.

        # Returns:
        #     str: The solved Sudoku puzzle in string format.
        # """    
        
        # Set up puzzles in numpy and fill 3D array with possibilities
        puzzle_2d, options_3d = self._string_to_np_puzzle(unsolved_sudoku)
        

        while True:
            prev_puzzle_2d: np.ndarray = puzzle_2d

            it = np.nditer(puzzle_2d, flags=['multi_index'])
            known_cells = [(it.multi_index, v) for v in it if v != 0]
            for cell in known_cells:
                # Isolate 2D matrix of this cell's options
                options_slice = options_3d[:, :, cell[1]-1]

                options_slice[cell[0][0], :] = 0 # Set column to zero
                options_slice[:, cell[0][1]] = 0 # Set row to zero
                box = (int(cell[0][0]/3), int(cell[0][1]/3)) # Identify which box the cell belongs to
                options_slice[(box[0]*3):(box[0]*3+3), 
                            (box[1]*3):(box[1]*3+3)] = 0 # Set box to zero
                options_slice[cell[0]] = 1 # Set this cell back to one
            

            # total_options: int = options_3d.sum()
            puzzle_2d = (options_3d.argmax(axis=2)+1)
            puzzle_2d[options_3d.sum(axis=2)!=1] = 0

            # Break out of while loop if no improvement is made or board is solved
            if np.all(puzzle_2d == prev_puzzle_2d):
                break
            elif puzzle_2d.sum() == 9*45:
                return self._np_puzzle_to_string(options_3d)
        
        num_possibilities: int = options_3d.sum(axis=2).prod()

        # Return answer if only one possibility left
        if num_possibilities == 1:
            return self._np_puzzle_to_string(options_3d)

        if num_possibilities >= max_iterations or num_possibilities < 0:
            logging.warning(f'More than {max_iterations:_} combinations to check, aborting...')
            return None

        it = np.nditer(puzzle_2d, flags=['multi_index'])
        options_idx = [[(*it.multi_index, int(d)) for d in np.nditer(np.where(options_3d[*it.multi_index,:] == 1)[0])] for v in it if v == 0]
        options_idx

        # Create the generator
        generator = self._unique_combinations(*options_idx)

        # Set-up first option
        for idx in next(generator): 
            options_3d[*idx[1][:2], :] = 0
            options_3d[*idx[1]] = 1
        
        # Return first option if valid
        if self.validate_solution(options_3d):
            return self._np_puzzle_to_string(options_3d)

        # Iterate over other options
        for changes in generator:
            for idx in changes:
                options_3d[*idx[0]] = 0
                options_3d[*idx[1]] = 1
            
            if self.validate_solution(options_3d):
                return self._np_puzzle_to_string(options_3d)
        
        


    
