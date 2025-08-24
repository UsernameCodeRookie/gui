#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>

// CUDA Kernel: 保留 K 参数，但假设 K=1
__global__ void conv2d_kernel(float* input, float* weight, float* output, int H,
                              int W, int I, int J, int C, int K) {
  int Ho = H - I + 1;
  int Wo = W - J + 1;

  int h = blockIdx.y * blockDim.y + threadIdx.y;
  int w = blockIdx.x * blockDim.x + threadIdx.x;
  int k = blockIdx.z * blockDim.z + threadIdx.z;

  if (h < Ho && w < Wo && k < K) {  // K=1
    float sum = 0.0f;
    for (int i = 0; i < I; i++) {
      for (int j = 0; j < J; j++) {
        for (int c = 0; c < C; c++) {
          int in_idx = ((h + i) * W + (w + j)) * C + c;
          int wt_idx = ((i * J + j) * C + c) * K + k;
          sum += input[in_idx] * weight[wt_idx];
        }
      }
    }
    int out_idx = (h * Wo + w) * K + k;
    output[out_idx] = sum;
  }
}

void conv2d(float* input, float* weight, float* output, int H, int W, int I,
            int J, int C, int K) {
  int Ho = H - I + 1;
  int Wo = W - J + 1;

  size_t in_size = H * W * C * sizeof(float);
  size_t wt_size = I * J * C * K * sizeof(float);  // K=1 时仍合法
  size_t out_size = Ho * Wo * K * sizeof(float);   // K=1 时仍合法

  float *d_input, *d_weight, *d_output;
  cudaMalloc(&d_input, in_size);
  cudaMalloc(&d_weight, wt_size);
  cudaMalloc(&d_output, out_size);

  cudaMemcpy(d_input, input, in_size, cudaMemcpyHostToDevice);
  cudaMemcpy(d_weight, weight, wt_size, cudaMemcpyHostToDevice);

  dim3 block(16, 16, 1);
  dim3 grid((Wo + block.x - 1) / block.x, (Ho + block.y - 1) / block.y,
            (K + block.z - 1) / block.z);  // K=1 → grid.z=1

  conv2d_kernel<<<grid, block>>>(d_input, d_weight, d_output, H, W, I, J, C, K);

  cudaMemcpy(output, d_output, out_size, cudaMemcpyDeviceToHost);

  cudaFree(d_input);
  cudaFree(d_weight);
  cudaFree(d_output);
}

int main() {
  // 参数: H=7, W=56, I=3, J=3, C=32, K=1
  int H = 7, W = 56, I = 3, J = 3, C = 32, K = 32;
  int Ho = H - I + 1;
  int Wo = W - J + 1;

  float* input = (float*)malloc(H * W * C * sizeof(float));
  float* weight = (float*)malloc(I * J * C * K * sizeof(float));
  float* output = (float*)malloc(Ho * Wo * K * sizeof(float));

  for (int idx = 0; idx < H * W * C; idx++) input[idx] = 1.0f;
  for (int idx = 0; idx < I * J * C * K; idx++) weight[idx] = 0.1f;

  conv2d(input, weight, output, H, W, I, J, C, K);

  // for (int h = 0; h < Ho; h++) {
  //   for (int w = 0; w < Wo; w++) {
  //     int out_idx = (h * Wo + w) * K;
  //     printf("out[%d,%d,0] = %.2f\n", h, w, output[out_idx]);
  //   }
  // }

  free(input);
  free(weight);
  free(output);
  return 0;
}
