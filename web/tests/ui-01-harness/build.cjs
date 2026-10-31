const fs = require('node:fs/promises');
const path = require('node:path');
const webRoot = path.resolve(__dirname, '../..');
const outputRoot = path.join(path.dirname(webRoot), 'output', 'ui-01-harness');
const tsxPackage = require.resolve('tsx/package.json', { paths: [webRoot] });
const esbuildPath = require.resolve('esbuild', { paths: [path.dirname(tsxPackage)] });
const esbuild = require(esbuildPath);

async function buildHarness() {
  await fs.mkdir(outputRoot, { recursive: true });
  const result = await esbuild.build({
    absWorkingDir: webRoot,
    entryPoints: ['tests/ui-01-harness/entry.tsx'],
    outfile: path.join(outputRoot, 'harness.js'),
    bundle: true,
    platform: 'browser',
    format: 'iife',
    jsx: 'automatic',
    target: ['es2022'],
    tsconfig: path.join(webRoot, 'tsconfig.json'),
    define: { 'process.env.NODE_ENV': '"development"' },
    metafile: true,
    sourcemap: false,
    plugins: [{
      name: 'ui-01-test-only-shims',
      setup(build) {
        build.onResolve({ filter: /^@clerk\/nextjs$/ }, () => ({ path: path.join(__dirname, 'clerk-shim.ts') }));
        build.onResolve({ filter: /^next\/link$/ }, () => ({ path: path.join(__dirname, 'link-shim.tsx') }));
      },
    }],
  });
  const inputs = Object.keys(result.metafile.inputs);
  if (!inputs.some(file => file.endsWith('components/forms/account-workbench.tsx')) || !inputs.some(file => file.endsWith('components/forms/form-workbench.tsx'))) throw new Error('Actual workbench components are missing from the test bundle.');
  if (inputs.some(file => /node_modules[\\/].*@clerk[\\/]/.test(file))) throw new Error('Real Clerk code must not enter the isolated harness.');
  await fs.writeFile(path.join(outputRoot, 'index.html'), '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>UI-01 TEST HARNESS — SYNTHETIC ONLY</title><link rel="stylesheet" href="/harness.css"></head><body><div id="harness-root"></div><script src="/harness.js" defer></script></body></html>');
  return { outputRoot, esbuildPath, componentCount: inputs.filter(file => file.includes('components/')).length };
}

module.exports = { buildHarness };
if (require.main === module) buildHarness().then(info => console.log(JSON.stringify({ ...info, status: 'TEST HARNESS BUILT' }))).catch(error => { console.error(error.message); process.exitCode = 1; });
