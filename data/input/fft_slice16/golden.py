import numpy as np
import sys
from itertools import islice

# This script models FFT computation based on CGRA architecture
# and compares the error with numpy's FFT calculation.

def bit_reverse(n, bits):
    reversed_n = 0
    for i in range(bits):
        if (n & (1 << i)):
            reversed_n |= 1 << (bits - 1 - i)
    return reversed_n

def calculate_magnitudes(complex_list):
    return [abs(c) for c in complex_list]

def fft(memdata_filename, golden_filename):
    # Parameters
    N = 1024  # sequence length
    freq = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]  # frequencies in Hz
    samp_rate = N * 1000  # sampling rate in Hz

    log2N = int(np.log2(N))
    # generate time series
    t = np.arange(N) / samp_rate
    # generate combined complex sine waves and twiddle factors
    input_c = sum(np.exp(2j * np.pi * f * t) for f in freq) * 10
    w_c = np.exp(-2j * np.pi * np.arange(N//2) / N)

    # bit-reversed twiddle factors
    w_c_rev = np.zeros_like(w_c)
    for i in range(0, N//2):
        index = bit_reverse(i, log2N-1)
        w_c_rev[index] = w_c[i]
        
    golden_result = np.fft.fft(input_c, N)
    golden_result_rev = np.zeros_like(golden_result)
    for i in range(0, N):
        index = bit_reverse(i, log2N)
        golden_result_rev[index] = golden_result[i]

    # print input waves real and imaginary parts with 7 decimal places
    print("Input Wave:")
    for c in input_c:
        print(f"{c.real:6.7f} + {c.imag:6.7f}j\t", end=' ')
    print()

    # print scaling factors (twiddle factors)
    print("Scaling Factors:")
    for w in w_c:
        print(f"{w.real:6.7f} + {w.imag:6.7f}j\t", end=' ')
    print()

    # convert complex input to real-imag pairs
    input_ri = []
    for value in input_c:
        input_ri.append(value.real)
        input_ri.append(value.imag)

    w_c_rev_ri = []
    for value in w_c_rev:
        w_c_rev_ri.append(value.real)
        w_c_rev_ri.append(value.imag)
        
    output_ri = []
    for value in golden_result_rev:
        output_ri.append(value.real)
        output_ri.append(value.imag)

    max_address = 40000

    # write to specified file with input and weights stored at specific addresses
    with open(memdata_filename, "w") as f:
        for address in range(max_address):
            if 10240 <= address < 10240 + len(input_ri):
                value = input_ri[address - 10240]
            elif 20480 <= address < 20480 + len(w_c_rev_ri):
                value = w_c_rev_ri[address - 20480]
            else:
                value = 0
            f.write(f"{value:.7f}\n")
            
    with open(golden_file, "w") as f:
        for address in range(max_address):
            if 10240 <= address < 10240 + len(input_ri):
                value = input_ri[address - 10240]
            elif 20480 <= address < 20480 + len(w_c_rev_ri):
                value = w_c_rev_ri[address - 20480]
            elif 0<=address<0+len(output_ri):
                assert len(output_ri) < 10240, "Address exceeds output size"
                value = output_ri[address]
            else:
                value = 0.0
            f.write(f"{value:.7f}\n")

if __name__ == "__main__":
    mem_file = sys.argv[1]
    golden_file = sys.argv[2]
    fft(mem_file, golden_file)
