import numpy as np
import sys

def gemm(memdata_filename, golden_filename):
    """
    Generates input matrices for large GEMM, writes them to memory layout,
    computes the golden output (M x K @ K x N), and writes both to files.
    Also prints each slice's starting address for C and A.
    """

    # Slice and matrix sizes
    SLICE_M = 64
    NUM_SLICES = 16
    M = SLICE_M * NUM_SLICES
    N = K = 64

    # Calculate matrix sizes
    size_C = M * N       # Output matrix (C)
    size_A = M * K       # Input matrix A
    size_B = K * N       # Input matrix B

    # Updated memory address layout (in float32 word units)
    ADDR_MN = 0                       # C output starts here
    ADDR_MK = ADDR_MN + size_C       # A input starts here
    ADDR_KN = ADDR_MK + size_A       # B input starts here

    print("Memory layout:")
    print(f"  C output starts at address {ADDR_MN}, size {size_C} floats")
    print(f"  A input starts at address {ADDR_MK}, size {size_A} floats")
    print(f"  B input starts at address {ADDR_KN}, size {size_B} floats")

    # Generate input matrices
    A = np.random.rand(M, K).astype(np.float32)
    B = np.random.rand(K, N).astype(np.float32)
    C = A @ B  # Matrix multiply result

    print("Matrix A (M x K): shape =", A.shape)
    print("Matrix B (K x N): shape =", B.shape)
    print("Matrix C = A @ B (M x N): shape =", C.shape)

    # Flatten for memory
    A_flat = A.flatten()
    B_flat = B.flatten()
    C_flat = C.flatten()

    # === Print per-slice info (formatted like conv) ===
    print(f"\n[Per-slice info (base {SLICE_M} rows per slice)]")
    for i in range(NUM_SLICES):
        slice_start_row = i * SLICE_M

        c_index = slice_start_row * N
        a_index = slice_start_row * K

        c_addr = ADDR_MN + c_index
        a_addr = ADDR_MK + a_index

        print(f"Slice {i}:")
        print(f"  C Output Start Address: {c_addr}")
        print(f"  A Input  Start Address: {a_addr}")

    # === Memory bounds ===
    max_address = ADDR_KN + size_B + 1024  # Safety buffer

    # === Write memdata file ===
    with open(memdata_filename, "w") as f:
        for addr in range(max_address):
            if ADDR_MK <= addr < ADDR_MK + size_A:
                value = A_flat[addr - ADDR_MK]
            elif ADDR_KN <= addr < ADDR_KN + size_B:
                value = B_flat[addr - ADDR_KN]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

    # === Write golden file (C, A, B) ===
    with open(golden_filename, "w") as f:
        for addr in range(max_address):
            if ADDR_MN <= addr < ADDR_MN + size_C:
                value = C_flat[addr - ADDR_MN]
            elif ADDR_MK <= addr < ADDR_MK + size_A:
                value = A_flat[addr - ADDR_MK]
            elif ADDR_KN <= addr < ADDR_KN + size_B:
                value = B_flat[addr - ADDR_KN]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gemm_golden.py mem_output.txt golden_output.txt")
        sys.exit(1)

    mem_file = sys.argv[1]
    golden_file = sys.argv[2]

    gemm(mem_file, golden_file)
