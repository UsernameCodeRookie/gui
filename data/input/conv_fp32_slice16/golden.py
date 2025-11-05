import numpy as np
import sys

def conv2d_numpy(input_tensor, weight, bias=None, stride=1, padding=1):
    """
    NumPy implementation of 2D convolution
    
    Args:
        input_tensor: shape (C, H, W)
        weight: shape (K, C, I, J)
        bias: shape (K,) or None
        stride: stride for convolution
        padding: padding size
    
    Returns:
        output: shape (K, H_out, W_out)
    """
    C, H, W = input_tensor.shape
    K, C_w, I, J = weight.shape
    
    assert C == C_w, f"Input channels mismatch: {C} vs {C_w}"
    
    # Calculate output dimensions
    H_out = (H + 2 * padding - I) // stride + 1
    W_out = (W + 2 * padding - J) // stride + 1
    
    # Pad input
    if padding > 0:
        padded_input = np.pad(input_tensor, ((0, 0), (padding, padding), (padding, padding)), mode='constant')
    else:
        padded_input = input_tensor
    
    # Initialize output
    output = np.zeros((K, H_out, W_out), dtype=np.float32)
    
    # Perform convolution
    for k in range(K):
        for h in range(H_out):
            for w in range(W_out):
                h_start = h * stride
                h_end = h_start + I
                w_start = w * stride
                w_end = w_start + J
                
                # Extract patch
                patch = padded_input[:, h_start:h_end, w_start:w_end]
                
                # Compute convolution for this output position
                conv_result = np.sum(patch * weight[k])
                
                # Add bias if provided
                if bias is not None:
                    conv_result += bias[k]
                
                output[k, h, w] = conv_result
    
    return output

def relu_numpy(x):
    """NumPy implementation of ReLU activation"""
    return np.maximum(0, x)

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
    x = np.random.randn(1, C, H, W).astype(np.float32)              # Input shape: NCHW
    w = np.random.randn(K, C, I, J).astype(np.float32)              # Weight shape: KCIJ
    b = np.ones(K, dtype=np.float32) if Has_bias else None  # Optional bias

    # Perform 2D convolution
    y = conv2d_numpy(x[0], w, bias=b if Has_bias else None, stride=Stride, padding=1)

    # Apply activation if specified
    if SFU == "relu":
        y = relu_numpy(y)

    # Remove batch dimension for memory layout
    x = x[0]  # CHW
    # y is already CHW from conv2d_numpy

    # Flatten tensors for memory layout (row-major)
    x_flat = x.transpose(0, 1, 2).reshape(-1)     # CHW → flat
    w_flat = w.transpose(0, 1, 2, 3).reshape(-1)  # KCIJ → flat
    y_flat = y.transpose(0, 1, 2).reshape(-1)     # KHW → flat

    # Flatten bias if used
    if Has_bias:
        b_reshaped = b[:, None, None] * np.ones((K, y.shape[1], y.shape[2]))  # Broadcast to KxHxW
        b_flat = b_reshaped.reshape(-1)
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
