/**
 * Shared file icon name resolver.
 * Maps file names/extensions to Icon component names.
 */

export function fileIconName(name: string, type: string = 'file'): string {
	if (type === 'directory') return 'folder';
	const ext = name.split('.').pop()?.toLowerCase() ?? '';
	if (name === 'Dockerfile') return 'docker';
	if (name === 'LICENSE' || name === 'LICENSE.md') return 'page-text';
	if (name.endsWith('.lock')) return 'lock';
	switch (ext) {
		case 'md': return 'page-text';
		case 'ts': case 'tsx': case 'js': case 'jsx':
		case 'py': case 'rs': case 'go': case 'java':
		case 'c': case 'cpp': case 'h': case 'hpp':
		case 'rb': case 'php': case 'swift': case 'kt':
		case 'svelte': case 'vue':
			return 'code';
		case 'json': case 'yaml': case 'yml': case 'toml':
		case 'ini': case 'cfg': case 'conf':
			return 'settings';
		case 'sh': case 'bash': case 'zsh':
			return 'terminal';
		case 'css': case 'html': case 'xml':
			return 'code';
		default: return 'empty-page';
	}
}
