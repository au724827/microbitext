<script lang="ts">
	import { scope } from '@i18n';
	import { FriendlyError } from '../../helpers/friendly_error';
	import {
		cloneImage,
		COMMON_IMAGES,
		imageMatrixToInt,
		intToImageMatrix,
		isEmptyImage
	} from '../../helpers/images';
	import { clientMicrobitService } from '../../services/client_microbit.svelte';
	import { Features, features } from '../../services/features.svelte';
	import FeaturesDropdown from '../Components/FeaturesDropdown.svelte';
	import ImageMatrixRenderer from '../Components/ImageMatrixRenderer.svelte';
	import InteractiveBitString from '../Components/InteractiveBitString.svelte';

	const scopedT = scope('clientInterface');

	let error: string | undefined = $state();
	let privateKeyVisible = $state(true);
	let newPkName = $state('');
	let newPkImage = $state(cloneImage(COMMON_IMAGES.EMPTY));
	let addError: string | undefined = $state();

	const asymmetricEnabled = $derived(features.isActive(Features.Asymmetric));


	function handleConnect() {
		error = undefined;
		clientMicrobitService.connect().catch((err) => (error = err));
	}

	function handleDisconnect() {
		clientMicrobitService.disconnect().catch((err) => (error = err));
	}

	function handleKeyGen() {
		error = undefined;
		privateKeyVisible = true;
		clientMicrobitService.requestKeyGen().catch((err) => (error = err));
	}

	function handleAddPublicKey() {
		addError = undefined;
		const name = newPkName.trim();
		if (!name) {
			addError = scopedT('missingName');
			return;
		}
		if (isEmptyImage(newPkImage)) {
			addError = scopedT('emptyPublicKey');
			return;
		}
		const added = clientMicrobitService.addLearnedPublicKey(name, imageMatrixToInt(newPkImage));
		if (!added) {
			addError = scopedT('duplicateName');
			return;
		}
		newPkName = '';
		newPkImage = cloneImage(COMMON_IMAGES.EMPTY);
	}

	function handleRemovePublicKey(name: string) {
		clientMicrobitService.removeLearnedPublicKey(name);
	}

	$effect(() => {
		if (!asymmetricEnabled && clientMicrobitService.connected) {
			void clientMicrobitService.disconnect();
		}
	});
</script>

<main>
	<header>
		<h1>{scopedT('title')}</h1>
		<p class="subheading">{scopedT('subtitle')}</p>
	</header>

	<hr />


	{#if !asymmetricEnabled}
		<section class="connect">
			<p>{scopedT('asymmetricRequired')}</p>
		</section>
	{:else}
		{#if !clientMicrobitService.connected || !clientMicrobitService.identified}
			<section class="connect">
				<p>{scopedT('connectDescription')}</p>
				<button class="large" onclick={handleConnect}>{scopedT('connect')}</button>
				{#if error}
					<span class="error">{FriendlyError.getMessage(error)}</span>
				{/if}
			</section>
		{:else}
			<section class="actions">
				<p class="status">{scopedT('connected')}</p>
				{#if clientMicrobitService.deviceName}
					<p class="device-name">{clientMicrobitService.deviceName}</p>
				{/if}
				<button class="large" onclick={handleKeyGen}>{scopedT('keyGen')}</button>
				{#if error}
					<span class="error">{FriendlyError.getMessage(error)}</span>
				{/if}
			</section>
		{/if}

		{#if clientMicrobitService.privateKey !== null && clientMicrobitService.publicKey !== null}
			<div class="keys">
				<article class="key-card private">
					<h2>{scopedT('privateKey')}</h2>
					<p class="key-hint">{scopedT('keepSecret')}</p>
					{#if privateKeyVisible}
						<ImageMatrixRenderer
							matrix={intToImageMatrix(clientMicrobitService.privateKey)}
							caption={scopedT('privateKey')}
						/>
						<p class="bits">
							{scopedT('bitString')}: {groupedBits(clientMicrobitService.privateKey)}
						</p>
					{:else}
						<div class="key-hidden" role="img" aria-label={scopedT('privateKeyHidden')}>
							<p>{scopedT('privateKeyHidden')}</p>
						</div>
					{/if}
					<button class="transparent" onclick={() => (privateKeyVisible = !privateKeyVisible)}>
						{privateKeyVisible ? scopedT('hidePrivateKey') : scopedT('showPrivateKey')}
					</button>
				</article>
				<article class="key-card public">
					<h2>{scopedT('publicKey')}</h2>
					<p class="key-hint">{scopedT('shareFreely')}</p>
					<ImageMatrixRenderer
						matrix={intToImageMatrix(clientMicrobitService.publicKey)}
						caption={scopedT('publicKey')}
					/>
					<p class="bits">{scopedT('bitString')}: {groupedBits(clientMicrobitService.publicKey)}</p>
				</article>
			</div>
		{/if}

		<section class="learned">
			<h2>{scopedT('learnedKeys')}</h2>
			<p class="key-hint">{scopedT('learnedKeysHint')}</p>

			{#if clientMicrobitService.learnedPublicKeys.length === 0}
				<p class="key-hint">{scopedT('noLearnedKeys')}</p>
			{:else}
				<ul class="learned-list">
					{#each clientMicrobitService.learnedPublicKeys as entry (entry.name)}
						<li>
							<div class="learned-item">
								<ImageMatrixRenderer
									matrix={intToImageMatrix(entry.publicKey)}
									caption={entry.name}
								/>
								<span class="learned-name">{entry.name}</span>
							</div>
							<button class="transparent" onclick={() => handleRemovePublicKey(entry.name)}>
								{scopedT('removePublicKey')}
							</button>
						</li>
					{/each}
				</ul>
			{/if}

			<article class="add-pk">
				<h3>{scopedT('addPublicKey')}</h3>
				<div class="input-field">
					<label for="pk-name">{scopedT('otherDeviceName')}</label>
					<div class="input-container">
						<input
							id="pk-name"
							type="text"
							bind:value={newPkName}
							placeholder={scopedT('otherDeviceNamePlaceholder')}
						/>
					</div>
				</div>
				<InteractiveBitString bind:image={newPkImage} onHover={() => {}} />
				<button class="large" onclick={handleAddPublicKey}>{scopedT('add')}</button>
				{#if addError}
					<span class="error">{addError}</span>
				{/if}
			</article>
		</section>

		{#if clientMicrobitService.connected && clientMicrobitService.identified}
			<button class="large transparent" onclick={handleDisconnect}>{scopedT('disconnect')}</button>
		{/if}
	{/if}
</main>

<style>
	main {
		padding: 24px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.25rem;
		max-width: 720px;
		margin: 0 auto;
	}

	header {
		text-align: center;
	}

	.connect,
	.actions,
	.learned {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 1rem;
		width: 100%;
		text-align: center;
	}

	.status {
		font-family: var(--heading);
		font-size: 1.25rem;
	}

	.device-name {
		font-family: var(--sans-display);
		font-size: 1.75rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--accent);
		margin: 0;
	}

	.keys {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		text-align: left;
		width: 100%;
	}

	.key-card,
	.add-pk {
		border: 1px solid var(--stroke);
		border-radius: 0.5rem;
		padding: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.key-card h2,
	.learned h2,
	.add-pk h3 {
		margin: 0;
		font-family: var(--heading);
		font-size: 1.1rem;
	}

	.key-hint {
		margin: 0;
		font-size: 0.9rem;
		color: var(--muted-grey);
	}

	.key-card.private {
		border-color: rgb(from var(--danger) r g b / 50%);
	}

	.key-card.public {
		border-color: rgb(from var(--accent) r g b / 50%);
	}

	.bits {
		margin: 0;
		font-family: var(--mono);
		font-size: 0.75rem;
		color: var(--muted-grey);
		word-break: break-all;
	}

	.key-hidden {
		aspect-ratio: 1;
		width: 100%;
		background-color: #111;
		border-radius: 0.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 1rem;
	}

	.key-hidden p {
		margin: 0;
		color: var(--muted-grey);
		font-family: var(--heading);
	}

	.learned {
		text-align: left;
	}

	.learned-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.learned-list li {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		border: 1px solid var(--stroke);
		border-radius: 0.5rem;
		padding: 0.5rem;
	}

	.learned-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-grow: 1;
	}

	.learned-item :global(.image-matrix) {
		max-width: 72px;
	}

	.learned-name {
		font-family: var(--sans-display);
		text-transform: uppercase;
	}

	.add-pk {
		text-align: left;
	}

	.error {
		color: var(--danger);
	}

	hr {
		width: 100%;
		border: none;
		border-top: 1px solid var(--stroke);
	}

	.feature-toggle {
		width: 100%;
		display: flex;
		justify-content: flex-end;
	}

	@media (max-width: 560px) {
		.keys {
			grid-template-columns: 1fr;
		}
	}
</style>
