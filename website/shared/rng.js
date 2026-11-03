/* Random number generators that reproduce the Python apps exactly, so a
 * class code gives the same game on this site as in the Streamlit version.
 *
 * - MG.PyRandom: CPython's `random.Random` (MT19937 seeded like
 *   random.Random(int)), with random, uniform, normalvariate, getrandbits,
 *   randrange, randint, choice, choices and sample — same algorithms as
 *   CPython 3.9–3.14.
 * - MG.NpGenerator: NumPy's `np.random.default_rng(SeedSequence)` —
 *   SeedSequence (incl. spawn), PCG64, and Generator.uniform / .normal
 *   (256-layer ziggurat).
 * - MG.pyRound / MG.fmt0: Python's round() (ties to even) and f"{x:.0f}",
 *   which JavaScript's Math.round / toFixed don't reproduce on exact .5s.
 */
(function () {
  "use strict";
  const MG = (globalThis.MG = globalThis.MG || {});

  // ── CPython random.Random ────────────────────────────────────────────
  const N = 624;
  const M = 397;
  const MATRIX_A = 0x9908b0df;
  const UPPER_MASK = 0x80000000;
  const LOWER_MASK = 0x7fffffff;
  // random.NV_MAGICCONST = 4 * exp(-0.5) / sqrt(2.0), as a literal so it
  // doesn't depend on the JS engine's exp() matching the C library's.
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

    /** Float in [0, 1) with 53 bits of randomness — random.random(). */
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

    /** random.getrandbits(k) for 1 <= k <= 32. */
    getrandbits(k) {
      if (k < 1 || k > 32) throw new RangeError("getrandbits supports 1..32 bits here");
      return this._genrandInt32() >>> (32 - k);
    }

    /** CPython _randbelow_with_getrandbits: uniform int in [0, n), n < 2**32. */
    _randbelow(n) {
      if (n <= 0) throw new RangeError("empty range");
      const k = 32 - Math.clz32(n); // n.bit_length()
      let r = this.getrandbits(k);
      while (r >= n) r = this.getrandbits(k);
      return r;
    }

    /** randrange(stop) or randrange(start, stop) (step 1). */
    randrange(start, stop) {
      if (stop === undefined) return this._randbelow(start);
      return start + this._randbelow(stop - start);
    }

    randint(a, b) {
      return this.randrange(a, b + 1);
    }

    choice(seq) {
      if (!seq.length) throw new RangeError("Cannot choose from an empty sequence");
      return seq[this._randbelow(seq.length)];
    }

    /** random.choices(population, weights, k) — bisect over cumulative weights. */
    choices(population, weights = null, k = 1) {
      const n = population.length;
      const out = [];
      if (weights === null) {
        for (let i = 0; i < k; i++) out.push(population[Math.floor(this.random() * n)]);
        return out;
      }
      const cum = [];
      let acc = 0;
      for (const w of weights) { acc += w; cum.push(acc); }
      const total = cum[cum.length - 1] + 0.0;
      if (!(total > 0.0) || !Number.isFinite(total)) throw new RangeError("Total of weights must be finite and > 0");
      const hi = n - 1;
      for (let i = 0; i < k; i++) {
        const x = this.random() * total;
        let lo = 0;
        let h = hi; // bisect_right(cum, x, 0, hi)
        while (lo < h) {
          const mid = (lo + h) >> 1;
          if (x < cum[mid]) h = mid; else lo = mid + 1;
        }
        out.push(population[lo]);
      }
      return out;
    }

    /** random.sample(population, k) — same pool/set strategy as CPython. */
    sample(population, k) {
      const n = population.length;
      if (k < 0 || k > n) throw new RangeError("Sample larger than population or is negative");
      const result = new Array(k);
      let setsize = 21;
      if (k > 5) setsize += 4 ** Math.ceil(Math.log(k * 3) / Math.log(4));
      if (n <= setsize) {
        const pool = Array.from(population);
        for (let i = 0; i < k; i++) {
          const j = this._randbelow(n - i);
          result[i] = pool[j];
          pool[j] = pool[n - i - 1];
        }
      } else {
        const selected = new Set();
        for (let i = 0; i < k; i++) {
          let j = this._randbelow(n);
          while (selected.has(j)) j = this._randbelow(n);
          selected.add(j);
          result[i] = population[j];
        }
      }
      return result;
    }
  }

  // ── NumPy SeedSequence + PCG64 + Generator ───────────────────────────
  const POOL_SIZE = 4;
  const INIT_A = 0x43b0d7e5;
  const MULT_A = 0x931e8875;
  const INIT_B = 0x8b51f9dd;
  const MULT_B = 0x58f38ded;
  const MIX_MULT_L = 0xca01f9dd;
  const MIX_MULT_R = 0x4973f715;
  const XSHIFT = 16;

  function intToUint32Words(n) {
    n = BigInt(n);
    if (n < 0n) throw new RangeError("expected a non-negative integer");
    if (n === 0n) return [0];
    const out = [];
    while (n > 0n) { out.push(Number(n & 0xffffffffn)); n >>= 32n; }
    return out;
  }

  function hashmix(value, hc) {
    value = (value ^ hc.v) >>> 0;
    hc.v = Math.imul(hc.v, MULT_A) >>> 0;
    value = Math.imul(value, hc.v) >>> 0;
    return (value ^ (value >>> XSHIFT)) >>> 0;
  }

  function mix(x, y) {
    const r = (Math.imul(MIX_MULT_L, x) - Math.imul(MIX_MULT_R, y)) >>> 0;
    return (r ^ (r >>> XSHIFT)) >>> 0;
  }

  /** numpy.random.SeedSequence(entropy, spawn_key). */
  class SeedSequence {
    constructor(entropy, spawnKey = []) {
      this.entropy = BigInt(entropy);
      this.spawnKey = spawnKey.slice();
      this.nChildrenSpawned = 0;
      let run = intToUint32Words(this.entropy);
      const spawn = this.spawnKey.flatMap(intToUint32Words);
      if (spawn.length && run.length < POOL_SIZE) run = run.concat(new Array(POOL_SIZE - run.length).fill(0));
      const entropyArray = run.concat(spawn);

      const pool = new Array(POOL_SIZE).fill(0);
      const hc = { v: INIT_A };
      for (let i = 0; i < POOL_SIZE; i++) pool[i] = hashmix(i < entropyArray.length ? entropyArray[i] : 0, hc);
      for (let s = 0; s < POOL_SIZE; s++) {
        for (let d = 0; d < POOL_SIZE; d++) if (s !== d) pool[d] = mix(pool[d], hashmix(pool[s], hc));
      }
      for (let s = POOL_SIZE; s < entropyArray.length; s++) {
        for (let d = 0; d < POOL_SIZE; d++) pool[d] = mix(pool[d], hashmix(entropyArray[s], hc));
      }
      this.pool = pool;
    }

    /** generate_state(nWords, uint64) as BigInts (little-endian word pairs). */
    generateState64(nWords) {
      let hc = INIT_B;
      const words = [];
      for (let i = 0; i < nWords * 2; i++) {
        let v = (this.pool[i % POOL_SIZE] ^ hc) >>> 0;
        hc = Math.imul(hc, MULT_B) >>> 0;
        v = Math.imul(v, hc) >>> 0;
        words.push((v ^ (v >>> XSHIFT)) >>> 0);
      }
      const out = [];
      for (let i = 0; i < nWords; i++) out.push(BigInt(words[2 * i]) | (BigInt(words[2 * i + 1]) << 32n));
      return out;
    }

    spawn(n) {
      const kids = [];
      for (let i = 0; i < n; i++) kids.push(new SeedSequence(this.entropy, this.spawnKey.concat([this.nChildrenSpawned + i])));
      this.nChildrenSpawned += n;
      return kids;
    }
  }

  const MASK64 = (1n << 64n) - 1n;
  const MASK128 = (1n << 128n) - 1n;
  const PCG_MULT = 0x2360ed051fc65da44385df649fccf645n;

  /** numpy.random.PCG64 (XSL-RR 128/64). */
  class PCG64 {
    constructor(seedSeq) {
      const [s0, s1, i0, i1] = seedSeq.generateState64(4);
      const initstate = (s0 << 64n) | s1;
      const initseq = (i0 << 64n) | i1;
      this.state = 0n;
      this.inc = ((initseq << 1n) | 1n) & MASK128;
      this._step();
      this.state = (this.state + initstate) & MASK128;
      this._step();
    }
    _step() { this.state = (this.state * PCG_MULT + this.inc) & MASK128; }
    nextUint64() {
      this._step();
      const s = this.state;
      const x = ((s >> 64n) ^ s) & MASK64;
      const rot = s >> 122n;
      return ((x >> rot) | (x << ((64n - rot) & 63n))) & MASK64;
    }
    nextDouble() { return Number(this.nextUint64() >> 11n) * (1.0 / 9007199254740992.0); }
  }

  // Ziggurat tables for random_standard_normal (Marsaglia & Tsang, 256
  // layers, 52-bit), built the same way as NumPy's ziggurat_constants.h.
  const ZIG_R = 3.6541528853610087963519472518;
  const ZIG_INV_R = 0.27366123732975827203338247596;
  const ZIG = (() => {
    const ki = new Array(256);
    const wi = new Array(256);
    const fi = new Array(256);
    const m52 = 4503599627370496.0; // 2**52
    const vn = 0.00492867323399;
    let dn = ZIG_R;
    let tn = dn;
    const q = vn / Math.exp(-0.5 * dn * dn);
    ki[0] = Math.floor((dn / q) * m52);
    ki[1] = 0;
    wi[0] = q / m52;
    wi[255] = dn / m52;
    fi[0] = 1.0;
    fi[255] = Math.exp(-0.5 * dn * dn);
    for (let i = 254; i >= 1; i--) {
      dn = Math.sqrt(-2.0 * Math.log(vn / dn + Math.exp(-0.5 * dn * dn)));
      ki[i + 1] = Math.floor((dn / tn) * m52);
      tn = dn;
      fi[i] = Math.exp(-0.5 * dn * dn);
      wi[i] = dn / m52;
    }
    return { ki, wi, fi };
  })();

  /** numpy.random.Generator(PCG64(seedSeq)) — the subset the games use. */
  class NpGenerator {
    constructor(seedSeq) { this.bg = new PCG64(seedSeq); }

    random() { return this.bg.nextDouble(); }

    /** Generator.uniform(low, high, size) */
    uniform(low, high, size) {
      const range = high - low;
      const out = [];
      for (let i = 0; i < size; i++) out.push(low + range * this.bg.nextDouble());
      return out;
    }

    standardNormal() {
      const { ki, wi, fi } = ZIG;
      for (;;) {
        let r = this.bg.nextUint64();
        const idx = Number(r & 0xffn);
        r >>= 8n;
        const sign = r & 1n;
        const rabs = Number((r >> 1n) & 0x000fffffffffffffn);
        let x = rabs * wi[idx];
        if (sign) x = -x;
        if (rabs < ki[idx]) return x;
        if (idx === 0) {
          for (;;) {
            const xx = -ZIG_INV_R * Math.log1p(-this.bg.nextDouble());
            const yy = -Math.log1p(-this.bg.nextDouble());
            // (rabs >> 8) & 1 — rabs is 52-bit, so no 32-bit JS shifts here.
            if (yy + yy > xx * xx) return Math.floor(rabs / 256) % 2 ? -(ZIG_R + xx) : ZIG_R + xx;
          }
        } else if ((fi[idx - 1] - fi[idx]) * this.bg.nextDouble() + fi[idx] < Math.exp(-0.5 * x * x)) {
          return x;
        }
      }
    }

    /** Generator.normal(loc, scale, size) */
    normal(loc, scale, size) {
      const out = [];
      for (let i = 0; i < size; i++) out.push(loc + scale * this.standardNormal());
      return out;
    }
  }

  // ── Python-compatible formatting ─────────────────────────────────────
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

  /** Python 3.12+'s built-in sum() over floats: Neumaier-compensated, so
   *  e.g. partial-credit fitness totals match the Python apps exactly. */
  function pySum(values) {
    let s = 0.0;
    let c = 0.0;
    for (const x of values) {
      const t = s + x;
      if (Math.abs(s) >= Math.abs(x)) c += (s - t) + x;
      else c += (x - t) + s;
      s = t;
    }
    return c && Number.isFinite(c) ? s + c : s;
  }

  /** A random share code like Python's "".join(random.choices(A-Z0-9, k=6)). */
  function newGameCode(k = 6) {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    const buf = new Uint32Array(k);
    globalThis.crypto.getRandomValues(buf);
    return Array.from(buf, (v) => chars[v % chars.length]).join("");
  }

  /** The games' code_to_seed(): int(sha256(CODE.strip().upper())[:12], 16). */
  function codeToSeed(code) {
    return BigInt("0x" + MG.sha256Hex(String(code).trim().toUpperCase()).slice(0, 12));
  }

  Object.assign(MG, { PyRandom, SeedSequence, PCG64, NpGenerator, pyRound, fmt0, pySum, newGameCode, codeToSeed });
})();
