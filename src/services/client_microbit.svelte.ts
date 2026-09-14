import { t } from '@i18n';
import { alert } from '../helpers/popup';
import { registerOnWindow } from '../helpers/window';
import { Features, features } from './features.svelte';
import { MicrobitSerialConnection } from './serial_connection';
import { generateKeyPair } from './elgamal'; 

export type LearnedPublicKey = {
	name: string;
	publicKey: number;
};

const KEYS_STORAGE = 'bit:chat:client-keys';

type StoredKeys = {
	privateKey: number | null;
	publicKey: number | null;
	learnedPublicKeys: LearnedPublicKey[];
};

/**
 * Serial service for a single client micro:bit (dummy.py).
 * Separate from microbitService, which talks to the server board only.
 */
class ClientMicrobitService {
	private static _instance: ClientMicrobitService;
	public static get instance(): ClientMicrobitService {
		if (!ClientMicrobitService._instance) {
			ClientMicrobitService._instance = new ClientMicrobitService();
		}
		return ClientMicrobitService._instance;
	}

	private serial: MicrobitSerialConnection = new MicrobitSerialConnection();

	public connected: boolean = $state(false);
	public identified: boolean = $state(false);
	public deviceName: string | null = $state(null);
	public privateKey: number | null = $state(null);
	public publicKey: number | null = $state(null);
	public learnedPublicKeys: LearnedPublicKey[] = $state([]);

	private constructor() {
		this.serial
			.addEventListener('message', this.onMessage.bind(this))
			.addEventListener('connected', () => (this.connected = true))
			.addEventListener('disconnected', () => {
				this.connected = false;
				this.identified = false;
				this.deviceName = null;
				this.privateKey = null;
				this.publicKey = null;
				this.learnedPublicKeys = [];
			});
	}

	public async connect() {
		if (!features.isActive(Features.Asymmetric)) {
			return;
		}
		this.identified = false;
		this.deviceName = null;
		await this.serial.connect();
		// Client firmware replies #dummy_<name>& whenever it sees UART traffic
		await this.serial.write('ping');
	}

	public async disconnect() {
		await this.serial.disconnect();
	}

	/**
	 * Discrete-log KEYGEN for the 25-bit toy system:
	 *   SK ← random in 1..p-2
	 *   PK ← g^SK mod p
	 * The pair is stored on this client page, not on the micro:bit.
	 */
	public async requestKeyGen() {
		if (!features.isActive(Features.Asymmetric) || !this.identified) {
			console.warn('Client keygen is only available when asymmetric encryption is enabled');
			return;
		}

		const { privateKey, publicKey } = generateKeyPair();
		this.privateKey = privateKey;
		this.publicKey = publicKey;
		this.saveKeys();
	}

	public addLearnedPublicKey(name: string, publicKey: number): boolean {
		const trimmed = name.trim().toLowerCase();
		if (!trimmed || publicKey <= 0) {
			return false;
		}
		if (this.learnedPublicKeys.some((entry) => entry.name === trimmed)) {
			return false;
		}

		this.learnedPublicKeys = [...this.learnedPublicKeys, { name: trimmed, publicKey }];
		this.saveKeys();
		void this.syncAllowedPublicKeys();
		return true;
	}

	public removeLearnedPublicKey(name: string) {
		this.learnedPublicKeys = this.learnedPublicKeys.filter((entry) => entry.name !== name);
		this.saveKeys();
		void this.syncAllowedPublicKeys();
	}

	public hasLearnedPublicKey(name: string): boolean {
		return this.learnedPublicKeys.some((entry) => entry.name === name);
	}

	private async syncAllowedPublicKeys() {
		if (!this.identified || !features.isActive(Features.Asymmetric)) {
			return;
		}
		const names = this.learnedPublicKeys.map((entry) => entry.name).join('_');
		await this.serial.write(names ? `pks_${names}` : 'pks');
	}

	private keysStorageKey(deviceName: string) {
		return `${KEYS_STORAGE}:${deviceName}`;
	}

	private loadKeys(deviceName: string) {
		try {
			const raw = localStorage.getItem(this.keysStorageKey(deviceName));
			if (!raw) {
				this.privateKey = null;
				this.publicKey = null;
				this.learnedPublicKeys = [];
				return;
			}
			const stored = JSON.parse(raw) as StoredKeys;
			this.privateKey = stored.privateKey ?? null;
			this.publicKey = stored.publicKey ?? null;
			this.learnedPublicKeys = stored.learnedPublicKeys ?? [];
		} catch (error) {
			console.error('Failed to load client keys:', error);
			this.privateKey = null;
			this.publicKey = null;
			this.learnedPublicKeys = [];
		}
	}

	private saveKeys() {
		if (!this.deviceName) {
			return;
		}
		const stored: StoredKeys = {
			privateKey: this.privateKey,
			publicKey: this.publicKey,
			learnedPublicKeys: this.learnedPublicKeys
		};
		localStorage.setItem(this.keysStorageKey(this.deviceName), JSON.stringify(stored));
	}

	private onMessage(message: string) {
		const messageCode = message.split('_')[0];

		if (messageCode === 'dummy') {
			this.deviceName = message.split('_')[1] || null;
			this.identified = true;
			if (this.deviceName) {
				this.loadKeys(this.deviceName);
			}
			if (features.isActive(Features.Asymmetric)) {
				void this.syncAllowedPublicKeys();
			}
			return;
		}

		if (messageCode === 'start') {
			alert(
				t('serial.serverMicrobitDetected.title'),
				t('serial.serverMicrobitDetected.text')
			);
			this.serial.disconnect();
			return;
		}

		console.debug('Client micro:bit message:', message);
	}
}

export const clientMicrobitService = ClientMicrobitService.instance;

registerOnWindow('clientMicrobitService', clientMicrobitService);
