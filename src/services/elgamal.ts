/**
 * Toy 25-bit ElGamal system.
 *
 * The micro:bit has a 5x5 LED matrix, so every value here (keys,
 * later ciphertext components) is a 25-bit number: 0..2^25-1.
 */

export const P = 33554393n; // 25-bit prime, according to https://t5k.org/curios/page.php/33550337.html
export const G = 3n; // primitive root, according to https://codingace.net/maths/primitive_root_of_prime.html

/*
* note, with this prime, there is 33,554,431-33,554,393 = 38 images that are not "encryptable". 
* we can not pick bigger prime, as this would mess with the LED matrix of the decryption.
* So we ensure that decryption is always possible, but encryption is not.
*/



// Should 0 be encryptable to show it has ciphertext of zeros (to visualize some lack of security)
export function isEncryptable(m: number): boolean {
	return m > 0 && m < Number(P);
}

export type KeyPair = {
	privateKey: number;
	publicKey: number;
};

/** base^exp mod mod, via BigInt so 25-bit x 25-bit products never overflow. */
function modPow(base: bigint, exp: bigint, mod: bigint): bigint {
	let result = 1n;
	base = base % mod;
	while (exp > 0n) {
		if (exp & 1n) result = (result * base) % mod;
		exp >>= 1n;
		base = (base * base) % mod;
	}
	return result;
}

/** Cryptographically-random BigInt in [1, max - 1]. */
function randomBigInt(max: bigint): bigint {
	const bits = max.toString(2).length;
	const bytes = Math.ceil(bits / 8);
	const buf = new Uint8Array(bytes);
	let value: bigint;
	do {
		crypto.getRandomValues(buf);
		value = 0n;
		for (const byte of buf) value = (value << 8n) | BigInt(byte);
		value &= (1n << BigInt(bits)) - 1n; // trim to avoid wasting draws
	} while (value < 1n || value >= max);
	return value;
}

/**
 * SK ← random in [1, P-2]
 * PK ← G^SK mod P
 */
export function generateKeyPair(): KeyPair {
	const sk = randomBigInt(P - 1n); // 1..P-2
	const pk = modPow(G, sk, P);
	return { privateKey: Number(sk), publicKey: Number(pk) };
}

export type Ciphertext = {
	c1: number;
	c2: number;
};

/**
 * Encrypt m (any value in [1, P-1] — i.e. almost any LED pattern) under
 * a recipient's public key. A fresh k each time is what makes this
 * asymmetric rather than just a shared secret: only someone holding x
 * can turn c1 back into the same shared value G^(k*x).
 */
export function encrypt(m: number, recipientPublicKey: number): Ciphertext {
	const y = BigInt(recipientPublicKey);
	const k = randomBigInt(P - 1n);
	const c1 = modPow(G, k, P);
	const sharedSecret = modPow(y, k, P);
	const c2 = (BigInt(m) * sharedSecret) % P;
	return { c1: Number(c1), c2: Number(c2) };
}

/** Decrypt using our own private key — this is the "only YOU" step. */
export function decrypt(ciphertext: Ciphertext, ownPrivateKey: number): number {
	const x = BigInt(ownPrivateKey);
	const c1 = BigInt(ciphertext.c1);
	const c2 = BigInt(ciphertext.c2);
	const sharedSecret = modPow(c1, x, P);
	const sharedSecretInv = modPow(sharedSecret, P - 2n, P); // Fermat inverse
	return Number((c2 * sharedSecretInv) % P);
}