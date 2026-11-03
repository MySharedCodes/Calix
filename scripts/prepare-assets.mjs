import { cpSync, mkdirSync } from 'node:fs';
mkdirSync('frontend/public/mathlive-fonts', { recursive: true });
cpSync('node_modules/mathlive/fonts', 'frontend/public/mathlive-fonts', { recursive: true });
