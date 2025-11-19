// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeRapide from 'starlight-theme-rapide';

// https://astro.build/config
export default defineConfig({
	site: 'https://preset-io.github.io/superset-sup/',
	base: '/superset-sup/',
	integrations: [
		starlight({
			title: 'sup CLI',
			description: 'Beautiful, modern interface for Superset and Preset workspaces',
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/preset-io/superset-sup' }
			],
			plugins: [
				starlightThemeRapide({
					starlightConfig: {
						accent: { 200: '#a7f3d0', 600: '#10b981', 900: '#047857', 950: '#022c22' }
					}
				})
			],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', link: '/introduction' },
						{ label: 'Installation', link: '/installation' },
						{ label: 'Quick Start', link: '/quick-start' },
					],
				},
				{
					label: 'Commands',
					autogenerate: { directory: 'commands' },
				},
				{
					label: 'Configuration',
					items: [
						{ label: 'Settings', link: '/config/settings' },
						{ label: 'Authentication', link: '/config/authentication' },
						{ label: 'Sync Configuration', link: '/config/sync' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Cross-Workspace Sync', link: '/guides/cross-workspace' },
						{ label: 'dbt Integration', link: '/guides/dbt-integration' },
						{ label: 'Multi-Asset Workflows', link: '/guides/multi-asset' },
					],
				},
			],
		}),
	],
});
