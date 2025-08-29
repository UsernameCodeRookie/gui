// #include <stdio.h>
#include <gem5/m5ops.h>
#include <stdlib.h>

// Conv2D: input [H][W][C], weight [I][J][C][K], output [Ho][Wo][K]
// H,W: input feature map size
// I,J: kernel size
// C: input channels
// K: output channels
void conv2d(float* input, float* weight, float* output, int H, int W, int I,
            int J, int C, int K) {
  int Ho = H - I + 1;
  int Wo = W - J + 1;

  // 遍历输出 feature map
  for (int h = 0; h < Ho; h++) {
    for (int w = 0; w < Wo; w++) {
      for (int k = 0; k < K; k++) {
        float sum = 0.0f;
        // 遍历 kernel
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
  }
}

int main() {
  m5_reset_stats(0, 0);
  // example: H=5, W=5, I=3, J=3, C=2, K=4
  int H = 7, W = 56, I = 3, J = 3, C = 32, K = 8;
  int Ho = H - I + 1;
  int Wo = W - J + 1;

  float* input = (float*)malloc(H * W * C * sizeof(float));
  float* weight = (float*)malloc(I * J * C * K * sizeof(float));
  float* output = (float*)malloc(Ho * Wo * K * sizeof(float));

  // 初始化输入和权重 (简单填充)
  for (int idx = 0; idx < H * W * C; idx++) input[idx] = 1.0f;
  for (int idx = 0; idx < I * J * C * K; idx++) weight[idx] = 0.1f;

  // 调用卷积
  conv2d(input, weight, output, H, W, I, J, C, K);

  // 打印结果
  // for (int h = 0; h < Ho; h++) {
  //   for (int w = 0; w < Wo; w++) {
  //     printf("[");
  //     for (int k = 0; k < K; k++) {
  //       int out_idx = (h * Wo + w) * K + k;
  //       printf(" %.2f", output[out_idx]);
  //     }
  //     printf(" ] ");
  //   }
  //   printf("\n");
  // }

  free(input);
  free(weight);
  free(output);
  m5_dump_stats(0, 0);
  return 0;
}
