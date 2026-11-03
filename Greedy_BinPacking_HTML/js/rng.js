/* Python-compatible random number generator.
 *
 * A faithful port of CPython's `random.Random` (MT19937 seeded through
 * init_by_array, exactly like `random.Random(int_seed)`), plus the three
 * methods the bin-packing generator uses: random(), uniform() and
 * normalvariate(). With the same integer seed it produces the same stream
 * as Python, so Challenge-mode instances match the Streamlit app seed for
 * seed.
 *
 * Also exports pyRound (Python's round(): ties go to the even integer) and
 * fmt0 (Python's f"{x:.0f}"), which JavaScript's Math.round / toFixed do not
 * reproduce on exact .5 values.
 */
(function () {
  "use strict";
  const BP = (globalThis.BP = globalThis.BP || {});

  const N = 624;
  const M = 397;
  const MATRIX_A = 0x9908b0df;
  const UPPER_MASK = 0x80000000;
  const LOWER_MASK = 0x7fffffff;
  // random.NV_MAGICCONST = 4 * exp(-0.5) / sqrt(2.0), copied as a literal so
  // it doesn't depend on the JS engine's exp() matching the C library's.
  const NV_MAGICCONST = 1.7155277699214135;

  class PyRandom {
    /** @param {number|bigint|string|null} seed  integer seed; null = random */
    constructor(seed) {
      this.mt = new Uint32Array(N);
      this.mti = N + 1;
      if (seed === null || seed === undefined) {
        const key = new Uint32Array(N);
        globalThis.crypto.getRandomValues(key);
        this._initByArray(Array.from(key));
      } else {
        this._initByArray(PyRandom.seedKey(seed));
      }
    }

    /** CPython random_seed(): abs(seed) split into 32-bit little-endian words. */
    static seedKey(seed) {
      let n = BigInt(seed);
      if (n < 0n) n = -n;
      if (n === 0n) return [0];
      const key = [];
      while (n > 0n) {
        key.push(Number(n & 0xffffffffn));
        n >>= 32n;
      }
      return key;
    }

    _initGenrand(s) {
      const mt = this.mt;
      mt[0] = s >>> 0;
      for (let i = 1; i < N; i++) {
        const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
        mt[i] = (Math.imul(1812433253, prev) + i) >>> 0;
      }
      this.mti = N;
    }

    _initByArray(key) {
      const mt = this.mt;
      this._initGenrand(19650218);
      let i = 1;
      let j = 0;
      for (let k = Math.max(N, key.length); k; k--) {
        const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
        mt[i] = ((mt[i] ^ Math.imul(prev, 1664525)) + key[j] + j) >>> 0;
        i++;
        j++;
        if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
        if (j >= key.length) j = 0;
      }
      for (let k = N - 1; k; k--) {
        const prev = mt[i - 1] ^ (mt[i - 1] >>> 30);
        mt[i] = ((mt[i] ^ Math.imul(prev, 1566083941)) - i) >>> 0;
        i++;
        if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
      }
      mt[0] = 0x80000000;
    }

    _genrandInt32() {
      const mt = this.mt;
      if (this.mti >= N) {
        let kk = 0;
        let y;
        for (; kk < N - M; kk++) {
          y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
          mt[kk] = mt[kk + M] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
        }
        for (; kk < N - 1; kk++) {
          y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK);
          mt[kk] = mt[kk + (M - N)] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
        }
        y = (mt[N - 1] & UPPER_MASK) | (mt[0] & LOWER_MASK);
        mt[N - 1] = mt[M - 1] ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0);
        this.mti = 0;
      }
      let y = mt[this.mti++];
      y ^= y >>> 11;
      y ^= (y << 7) & 0x9d2c5680;
      y ^= (y << 15) & 0xefc60000;
      y ^= y >>> 18;
      return y >>> 0;
    }

    /** Float in [0, 1) with 53 bits of randomness — same as random.random(). */
    random() {
      const a = this._genrandInt32() >>> 5;
      const b = this._genrandInt32() >>> 6;
      return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
    }

    uniform(a, b) {
      return a + (b - a) * this.random();
    }

    /** Kinderman–Monahan, identical to random.normalvariate(). */
    normalvariate(mu, sigma) {
      let z;
      for (;;) {
        const u1 = this.random();
        const u2 = 1.0 - this.random();
        z = (NV_MAGICCONST * (u1 - 0.5)) / u2;
        const zz = (z * z) / 4.0;
        if (zz <= -Math.log(u2)) break;
      }
      return mu + z * sigma;
    }
  }

  /** Python's round(x) for floats: nearest integer, exact ties to even. */
  function pyRound(x) {
    const f = Math.floor(x);
    const d = x - f;
    if (d > 0.5) return f + 1;
    if (d < 0.5) return f;
    return f % 2 === 0 ? f : f + 1;
  }

  /** Python's f"{x:.0f}" (toFixed rounds exact ties up instead of to even). */
  function fmt0(x) {
    if (x - Math.floor(x) === 0.5) return String(pyRound(x));
    return x.toFixed(0);
  }

  BP.PyRandom = PyRandom;
  BP.pyRound = pyRound;
  BP.fmt0 = fmt0;
})();
