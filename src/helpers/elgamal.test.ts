import { generateKeyPair, encrypt, decrypt, isEncryptable } from '../services/elgamal';

type ImageMatrix = number[][];

function imageMatrixToInt(matrix: ImageMatrix): number {
	return parseInt(matrix.flat().join(''), 2);
}

function intToImageMatrix(value: number): ImageMatrix {
	const bits = value.toString(2).padStart(25, '0').slice(-25);
	return [0, 1, 2, 3, 4].map((row) => [0, 1, 2, 3, 4].map((col) => Number(bits[row * 5 + col])));
}

function areImagesEqual(a: ImageMatrix, b: ImageMatrix): boolean {
	return JSON.stringify(a) === JSON.stringify(b);
}

function printImage(matrix: ImageMatrix): string {
	return matrix.map((row) => row.map((bit) => (bit ? '#' : '.')).join(' ')).join('\n');
}

const demoImages: Record<string, ImageMatrix> = {
	HEART: [
		[0, 1, 0, 1, 0],
		[1, 1, 1, 1, 1],
		[1, 1, 1, 1, 1],
		[0, 1, 1, 1, 0],
		[0, 0, 1, 0, 0]
	],
	DUCK: [
		[0, 1, 1, 0, 0],
		[1, 1, 1, 0, 0],
		[0, 1, 1, 1, 1],
		[0, 1, 1, 1, 0],
		[0, 0, 0, 0, 0]
	],
    HAPPY: [
			[0, 0, 0, 0, 0],
			[0, 1, 0, 1, 0],
			[0, 0, 0, 0, 0],
			[1, 0, 0, 0, 1],
			[0, 1, 1, 1, 0]
		],
	SAD: [
			[0, 0, 0, 0, 0],
			[0, 1, 0, 1, 0],
			[0, 0, 0, 0, 0],
			[0, 1, 1, 1, 0],
			[1, 0, 0, 0, 1]
		],
    FULL: [
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1]
        ],
    EMPTY: [
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ]
};

function runDemo() {
	const { privateKey, publicKey } = generateKeyPair();
	console.log(`Generated key pair — private: ${privateKey}, public: ${publicKey}\n`);

	for (const [name, image] of Object.entries(demoImages)) {
		const value = imageMatrixToInt(image);
		console.log(`=== ${name} (value: ${value}) ===`);
		console.log(printImage(image));

		if (!isEncryptable(value)) {
			console.log('--> not encryptable, skipping\n');
			continue;
		}

		const ciphertext = encrypt(value, publicKey);
		console.log(`encrypted --> c1: ${ciphertext.c1}, c2: ${ciphertext.c2}`);

		const decryptedValue = decrypt(ciphertext, privateKey);
		const decryptedImage = intToImageMatrix(decryptedValue);
		console.log(`decrypted --> value: ${decryptedValue}, matches original: ${areImagesEqual(decryptedImage, image)}\n`);
	}
}

runDemo();