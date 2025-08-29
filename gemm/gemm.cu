// gemm_gpgpusim_cycle.cu
#include <cuda_runtime.h>
#include <stdio.h>

#define CHECK_CUDA(call) do { \
    cudaError_t e = (call); \
    if (e!=cudaSuccess) { \
        printf("%s:%d CUDA Error %s\n",__FILE__,__LINE__,cudaGetErrorString(e)); \
        exit(1); \
    } \
} while(0)

#define TILE_M 16
#define TILE_N 16
#define TILE_K 16

// Pure kernel cycle version: C = A*B, MxK * KxN = MxN
__global__ void gemm_kernel(const float* __restrict__ A,
                            const float* __restrict__ B,
                            float* __restrict__ C,
                            int M, int N, int K) 
{
    __shared__ float sA[TILE_M][TILE_K];
    __shared__ float sB[TILE_K][TILE_N];

    int row = blockIdx.y * TILE_M + threadIdx.y;
    int col = blockIdx.x * TILE_N + threadIdx.x;

    float sum = 0.0f;

    // Loop over tiles
    for (int t=0; t<(K+TILE_K-1)/TILE_K; t++) {
        int tiled_k = t*TILE_K + threadIdx.x;

        // Load A tile
        if(row<M && tiled_k<K)
            sA[threadIdx.y][threadIdx.x] = A[row*K + tiled_k];
        else
            sA[threadIdx.y][threadIdx.x] = 0.f;

        // Load B tile
        int tiled_row = t*TILE_K + threadIdx.y;
        if(tiled_row<K && col<N)
            sB[threadIdx.y][threadIdx.x] = B[tiled_row*N + col];
        else
            sB[threadIdx.y][threadIdx.x] = 0.f;

        __syncthreads();

        // Compute tile
        #pragma unroll
        for(int k=0;k<TILE_K;k++)
            sum += sA[threadIdx.y][k]*sB[k][threadIdx.x];

        __syncthreads();
    }

    if(row<M && col<N)
        C[row*N + col] = sum;
}

// Host wrapper for GPGPU-Sim
void gemm_kernel_test(float* A, float* B, float* C, int M, int N, int K)
{
    float *dA, *dB, *dC;
    size_t sizeA = M*K*sizeof(float);
    size_t sizeB = K*N*sizeof(float);
    size_t sizeC = M*N*sizeof(float);

    CHECK_CUDA(cudaMalloc(&dA,sizeA));
    CHECK_CUDA(cudaMalloc(&dB,sizeB));
    CHECK_CUDA(cudaMalloc(&dC,sizeC));

    CHECK_CUDA(cudaMemcpy(dA,A,sizeA,cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(dB,B,sizeB,cudaMemcpyHostToDevice));

    dim3 block(TILE_N,TILE_M); // 16x16 threads = 256 threads per block
    dim3 grid((N+TILE_N-1)/TILE_N,(M+TILE_M-1)/TILE_M);

    // Launch kernel
    gemm_kernel<<<grid,block>>>(dA,dB,dC,M,N,K);

    // Wait for kernel finish
    CHECK_CUDA(cudaDeviceSynchronize());

    // Optional: don't copy back to host if purely measuring kernel cycle
    //CHECK_CUDA(cudaMemcpy(C,dC,sizeC,cudaMemcpyDeviceToHost));

    // Free device memory
    CHECK_CUDA(cudaFree(dA));
    CHECK_CUDA(cudaFree(dB));
    CHECK_CUDA(cudaFree(dC));
}

int main()
{
    int M=64,N=64,K=64;

    size_t sizeA=M*K;
    size_t sizeB=K*N;
    size_t sizeC=M*N;

    float* A = (float*)malloc(sizeA*sizeof(float));
    float* B = (float*)malloc(sizeB*sizeof(float));
    float* C = (float*)malloc(sizeC*sizeof(float));

    for(size_t i=0;i<sizeA;i++) A[i]=1.f;
    for(size_t i=0;i<sizeB;i++) B[i]=1.f;
    for(size_t i=0;i<sizeC;i++) C[i]=0.f;

    // Run kernel-only version
    gemm_kernel_test(A,B,C,M,N,K);

    // Pure cycle test: 不打印、不 memcpy 回 host

    free(A); free(B); free(C);
    return 0;
}
