/**
 * PWA lifecycle helpers: beforeinstallprompt and appinstalled event handling.
 */
import { toast } from 'svelte-sonner';

export function setupPwa(): () => void {
	let deferredPrompt: any = null;

	function onBeforeInstallPrompt(e: Event) {
		e.preventDefault();
		deferredPrompt = e;
		toast('Install cptr', {
			description: 'Install this app on your device for a better experience.',
			action: {
				label: 'Install',
				onClick: () => {
					if (!deferredPrompt) return;
					(deferredPrompt as any).prompt();
					(deferredPrompt as any).userChoice.then(
						(choiceResult: { outcome: string }) => {
							if (choiceResult.outcome === 'accepted') {
								console.log('[PWA] User accepted install prompt');
							} else {
								console.log('[PWA] User dismissed install prompt');
							}
							deferredPrompt = null;
						}
					);
				},
			},
			duration: 15000,
		});
	}

	function onAppInstalled() {
		console.log('[PWA] App installed successfully.');
		deferredPrompt = null;
		toast.success('cptr installed', {
			description: 'The app has been added to your device.',
		});
	}

	window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt);
	window.addEventListener('appinstalled', onAppInstalled);

	return () => {
		window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt);
		window.removeEventListener('appinstalled', onAppInstalled);
	};
}
