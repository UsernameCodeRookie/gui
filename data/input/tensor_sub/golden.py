import numpy as np
import sys

def vector_sub_int(memdata_filename, golden_filename):
    """
    Performs vector subtraction A - B = C with 256 int32 values.
    Stores memory layout according to LSU configuration.
    """

    VECTOR_LEN = 256

    # Memory address layout from LSU node
    ADDR_A = 500
    ADDR_B = 0
    ADDR_C = 1000
    MAX_ADDR = 4000  # Large enough to contain all three regions

    # Generate two random int32 vectors in a reasonable range
    A = np.random.randint(-1000, 1000, size=VECTOR_LEN, dtype=np.int32)
    B = np.random.randint(-1000, 1000, size=VECTOR_LEN, dtype=np.int32)
    C = A - B

    # Print all 3 vectors
    def print_vector(v, name):
        print(f"{name}:")
        for i in range(0, len(v), 8):  # 8 per line
            print("  " + "  ".join(f"{x:6d}" for x in v[i:i+8]))
        print()

    print_vector(A, "Vector A")
    print_vector(B, "Vector B")
    print_vector(C, "Vector C = A - B")

    # Write to memdata file (only A and B)
    with open(memdata_filename, "w") as f:
        for addr in range(MAX_ADDR):
            if ADDR_A <= addr < ADDR_A + VECTOR_LEN:
                value = A[addr - ADDR_A]
            elif ADDR_B <= addr < ADDR_B + VECTOR_LEN:
                value = B[addr - ADDR_B]
            else:
                value = 0
            f.write(f"{np.uint32(value)}\n")

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
                value = 0
            f.write(f"{np.uint32(value)}\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vector_sub_int_golden.py mem_output.txt golden_output.txt")
        sys.exit(1)

    mem_file = sys.argv[1]
    golden_file = sys.argv[2]

    vector_sub_int(mem_file, golden_file)
