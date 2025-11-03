# build/RISCV/gem5.opt configs/deprecated/example/se.py \
#     --cpu-type=TimingSimpleCPU \
#     --num-cpus=1 \
#     --cmd=tests/test-progs/conv/conv

# build/ARM/gem5.opt configs/deprecated/example/se.py \
#   --cpu-type=DerivO3CPU \
#   --num-cpus=1 \
#   --caches --l2cache \
#   --l1i_size=32kB --l1d_size=32kB --l2_size=1MB \
#   --l1i_assoc=2  --l1d_assoc=2  --l2_assoc=8 \
#   --cmd=tests/test-progs/conv/conv

build/ARM/gem5.opt configs/deprecated/example/se.py \
  --cpu-type=DerivO3CPU \
  --num-cpus=4 \
  --caches --l2cache \
  --l1i_size=32kB --l1d_size=32kB --l2_size=1MB \
  --l1i_assoc=2 --l1d_assoc=2 --l2_assoc=8 \
  --cmd="tests/test-progs/conv/conv;tests/test-progs/conv/conv;tests/test-progs/conv/conv;tests/test-progs/conv/conv" \
  --options="--size=256;--size=512;--size=128;--size=1024"

