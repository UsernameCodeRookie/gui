import numpy as np
import sys

def gemm(memdata_filename, golden_filename):
    """
    Generates input matrices for GEMM, writes them to memory layout,
    computes the golden output (M x K @ K x N), and writes both to files.
    """

    # Matrix sizes
    M = N = K = 64

    # Memory address offsets
    ADDR_MK = 4096
    ADDR_KN = 8192
    ADDR_MN = 0

    # Generate input matrices
    A = np.random.rand(M, K).astype(np.float32)  # MK
    B = np.random.rand(K, N).astype(np.float32)  # KN
    C = A @ B  # MN result

    print("Matrix A (M x K):")
    print(A)
    print("\nMatrix B (K x N):")
    print(B)
    print("\nMatrix C = A @ B (M x N):")
    print(C)

    # Flatten all matrices row-major
    A_flat = A.flatten()
    B_flat = B.flatten()
    C_flat = C.flatten()

    max_address = 40000

    # Write memory layout to memdata file
    with open(memdata_filename, "w") as f:
        for addr in range(max_address):
            if ADDR_MK <= addr < ADDR_MK + len(A_flat):
                value = A_flat[addr - ADDR_MK]
            elif ADDR_KN <= addr < ADDR_KN + len(B_flat):
                value = B_flat[addr - ADDR_KN]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

    # Write full memory snapshot to golden file including result
    with open(golden_filename, "w") as f:
        for addr in range(max_address):
            if ADDR_MN <= addr < ADDR_MN + len(C_flat):
                value = C_flat[addr - ADDR_MN]
            elif ADDR_MK <= addr < ADDR_MK + len(A_flat):
                value = A_flat[addr - ADDR_MK]
            elif ADDR_KN <= addr < ADDR_KN + len(B_flat):
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
