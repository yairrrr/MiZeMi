// Distribute the actual installed runtime-library notices with every Vite build.
import { readFile, writeFile } from 'node:fs/promises'
const packages = ['react', 'react-dom', 'scheduler', 'qrcode.react']
const notices = []
for (const name of packages) {
  const root = new URL(`../node_modules/${name}/`, import.meta.url)
  const metadata = JSON.parse(await readFile(new URL('package.json', root), 'utf8'))
  const license = await readFile(new URL('LICENSE', root), 'utf8')
  notices.push(`${name} ${metadata.version}\n${license}`)
}
await writeFile(new URL('../dist/THIRD_PARTY_NOTICES.txt', import.meta.url), notices.join('\n\n'))
