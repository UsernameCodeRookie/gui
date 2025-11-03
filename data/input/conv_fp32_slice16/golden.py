import numpy as np
import torch
import torch.nn.functional as F
import sys

def conv(memdata_filename, golden_filename):
    # Convolution Parameters
    BASE_K = 8  # base output channels per slice
    MULTIPLIER = 16
    K = BASE_K * MULTIPLIER  # total output channels = 128
    C = 8   # input channels
    H = 5   # input height
    W = 40  # input width
    I = 3   # kernel height
    J = 3   # kernel width
    Stride = 1
    Has_bias = 0
    SFU = 'relu'  # Optional post-processing (ReLU)

    # Memory layout base addresses
    Input_addr = 10000
    Weight_addr = 40000
    Bias_addr = 60000
    Output_addr = 70000
    max_address = 100000

    # Generate random input and weight tensors
    x = torch.randn(1, C, H, W, dtype=torch.float32)              # Input shape: NCHW
    w = torch.randn(K, C, I, J, dtype=torch.float32)              # Weight shape: KCIJ
    b = torch.ones(K, dtype=torch.float32) if Has_bias else None  # Optional bias

    # Perform 2D convolution
    y = F.conv2d(x, w, bias=b if Has_bias else None, stride=Stride, padding=1)

    # Apply activation if specified
    if SFU == "relu":
        y = F.relu(y)

    # Remove batch dimension for memory layout
    x = x[0]  # CHW
    y = y[0]  # KHW

    # Flatten tensors for memory layout (row-major)
    x_flat = x.permute(0, 1, 2).contiguous().view(-1).numpy()     # CHW → flat
    w_flat = w.permute(0, 1, 2, 3).contiguous().view(-1).numpy()  # KCIJ → flat
    y_flat = y.permute(0, 1, 2).contiguous().view(-1).numpy()     # KHW → flat

    # Flatten bias if used
    if Has_bias:
        b_reshaped = b[:, None, None].expand(K, y.shape[1], y.shape[2])  # Broadcast to KxHxW
        b_flat = b_reshaped.contiguous().view(-1).numpy()
    else:
        b_flat = None

    # Print tensor shapes
    print(f"Input Tensor shape (C,H,W): {x.shape}")
    print(f"Weight Tensor shape (K,C,I,J): {w.shape}")
    print(f"Output Tensor shape (K,H_out,W_out): {y.shape}")
    if Has_bias:
        print(f"Bias broadcast shape: {b_reshaped.shape}")

    # Print memory address ranges
    print(f"\n[Address ranges]")
    print(f"Input   [{Input_addr} - {Input_addr + len(x_flat) - 1}]")
    print(f"Weight  [{Weight_addr} - {Weight_addr + len(w_flat) - 1}]")
    if Has_bias:
        print(f"Bias    [{Bias_addr} - {Bias_addr + len(b_flat) - 1}]")
    print(f"Output  [{Output_addr} - {Output_addr + len(y_flat) - 1}]")

    # === Print per-slice start addresses (based on 8 output channels per slice) ===
    print("\n[Per-slice info (base 8 channels per slice)]")
    weight_per_channel = C * I * J
    output_H, output_W = y.shape[1], y.shape[2]
    output_per_channel = output_H * output_W

    for i in range(MULTIPLIER):  # 16 slices
        k_start = i * BASE_K  # Starting output channel index
        weight_offset = k_start * weight_per_channel
        output_offset = k_start * output_per_channel

        weight_address = Weight_addr + weight_offset
        output_address = Output_addr + output_offset

        print(f"Slice {i}:")
        print(f"  Output Channels [{k_start} - {k_start + BASE_K - 1}]")
        print(f"  Weight Start Address: {weight_address}")
        print(f"  Output Start Address: {output_address}")

    # === Write input tensors to memdata file ===
    with open(memdata_filename, "w") as f:
        for addr in range(max_address):
            if Input_addr <= addr < Input_addr + len(x_flat):
                value = x_flat[addr - Input_addr]
            elif Weight_addr <= addr < Weight_addr + len(w_flat):
                value = w_flat[addr - Weight_addr]
            elif Has_bias and Bias_addr <= addr < Bias_addr + len(b_flat):
                value = b_flat[addr - Bias_addr]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

    # === Write golden output (result + input weights) to golden file ===
    with open(golden_filename, "w") as f:
        for addr in range(max_address):
            if Output_addr <= addr < Output_addr + len(y_flat):
                value = y_flat[addr - Output_addr]
            elif Input_addr <= addr < Input_addr + len(x_flat):
                value = x_flat[addr - Input_addr]
            elif Weight_addr <= addr < Weight_addr + len(w_flat):
                value = w_flat[addr - Weight_addr]
            elif Has_bias and Bias_addr <= addr < Bias_addr + len(b_flat):
                value = b_flat[addr - Bias_addr]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python conv_golden.py memdata.txt golden.txt")
        sys.exit(1)

    mem_file = sys.argv[1]
    golden_file = sys.argv[2]
    conv(mem_file, golden_file)
