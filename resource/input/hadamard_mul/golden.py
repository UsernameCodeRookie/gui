import numpy as np
import sys

def vector_hadamard(memdata_filename, golden_filename):
    """
    Performs Hadamard product A * B = C with 256 float32 values.
    Stores memory layout according to LSU configuration.
    """

    VECTOR_LEN = 256

    # Memory address layout from LSU node
    ADDR_A = 0
    ADDR_B = 500
    ADDR_C = 1000
    MAX_ADDR = 4000  # Large enough to contain all three regions

    # Generate two random vectors
    A = np.random.rand(VECTOR_LEN).astype(np.float32)
    B = np.random.rand(VECTOR_LEN).astype(np.float32)
    C = A * B  # Hadamard product

    # Print all 3 vectors
    def print_vector(v, name):
        print(f"{name}:")
        for i in range(0, len(v), 8):  # 8 per line
            print("  " + "  ".join(f"{x:.4f}" for x in v[i:i+8]))
        print()

    print_vector(A, "Vector A")
    print_vector(B, "Vector B")
    print_vector(C, "Vector C = A * B")

    # Write to memdata file (only A and B)
    with open(memdata_filename, "w") as f:
        for addr in range(MAX_ADDR):
            if ADDR_A <= addr < ADDR_A + VECTOR_LEN:
                value = A[addr - ADDR_A]
            elif ADDR_B <= addr < ADDR_B + VECTOR_LEN:
                value = B[addr - ADDR_B]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

    # Write to golden file (includes result C)
    with open(golden_filename, "w") as f:
        for addr in range(MAX_ADDR):
            if ADDR_C <= addr < ADDR_C + VECTOR_LEN:
                value = C[addr - ADDR_C]
            elif ADDR_A <= addr < ADDR_A + VECTOR_LEN:
                value = A[addr - ADDR_A]
            elif ADDR_B <= addr < ADDR_B + VECTOR_LEN:
                value = B[addr - ADDR_B]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vector_hadamard.py mem_output.txt golden_output.txt")
        sys.exit(1)

    mem_file = sys.argv[1]
    golden_file = sys.argv[2]

    vector_hadamard(mem_file, golden_file)
