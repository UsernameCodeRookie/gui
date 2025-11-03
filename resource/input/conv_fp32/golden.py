import numpy as np
import torch
import torch.nn.functional as F
import sys

def conv(memdata_filename, golden_filename):
    # Parameters
    K = 32  # output channels
    C = 32  # input channels
    H = 7   # input height
    W = 56  # input width
    I = 3   # kernel height
    J = 3   # kernel width
    Stride = 1
    Has_bias = 0
    SFU = 'relu'

    # Memory layout base addresses
    Input_addr = 10000
    Weight_addr = 40000
    Bias_addr = 60000
    Output_addr = 80000
    max_address = 100000

    # Generate random input and weight
    # x = torch.randn(1, C, H, W, dtype=torch.float32)              # NCHW
    # w = torch.randn(K, C, I, J, dtype=torch.float32)              # KCIJ
    # b = torch.randn(K, dtype=torch.float32) if Has_bias else None

    x = torch.randn(1, C, H, W, dtype=torch.float32)              # NCHW
    w = torch.randn(K, C, I, J, dtype=torch.float32)              # KCIJ
    b = torch.ones(K, dtype=torch.float32) if Has_bias else None



    # Convolution (using PyTorch)
    y = F.conv2d(x, w, bias=b if Has_bias else None, stride=Stride, padding=1)

    if SFU == "relu":
        y = F.relu(y)

    # Remove batch dim for layout handling
    x = x[0]                # CHW
    y = y[0]                # KHW

    # Layout reshaping (explicitly match layout):
    x_flat = x.permute(0, 1, 2).contiguous().view(-1).numpy()     # CHW
    w_flat = w.permute(0, 1, 2, 3).contiguous().view(-1).numpy()  # KCIJ
    y_flat = y.permute(0, 1, 2).contiguous().view(-1).numpy()     # KHW

    if Has_bias:
        # Bias is broadcast to shape of output (K x H_out x W_out)
        b_reshaped = b[:, None, None].expand(K, y.shape[1], y.shape[2])  # K x H x W
        b_flat = b_reshaped.contiguous().view(-1).numpy()
    else:
        b_flat = None

    # Print shape info
    print(f"Input Tensor shape (C,H,W): {x.shape}")
    print(f"Weight Tensor shape (K,C,I,J): {w.shape}")
    print(f"Output Tensor shape (K,H_out,W_out): {y.shape}")
    if Has_bias:
        print(f"Bias broadcast shape: {b_reshaped.shape}")

    print(f"\n[Address ranges]")
    print(f"Input   [{Input_addr} - {Input_addr + len(x_flat) - 1}]")
    print(f"Weight  [{Weight_addr} - {Weight_addr + len(w_flat) - 1}]")
    if Has_bias:
        print(f"Bias    [{Bias_addr} - {Bias_addr + len(b_flat) - 1}]")
    print(f"Output  [{Output_addr} - {Output_addr + len(y_flat) - 1}]")

    # === Write to memdata ===
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

    # === Write to golden ===
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
