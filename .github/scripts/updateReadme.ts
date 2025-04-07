import fs from 'fs';
import path from 'path';

const COMMENTS_PATH = path.join('.github', 'config', 'folder-comments.json');
const README_PATH = 'README.md';

const comments: Record<string, string> = JSON.parse(fs.readFileSync(COMMENTS_PATH, 'utf-8'));
const items = fs.readdirSync('.', { withFileTypes: true });

const folders = items
  .filter((item) => item.isDirectory() && !item.name.startsWith('.git') && item.name !== 'node_modules')
  .map((folder) => {
    const comment = comments[folder.name] ? `  # ${comments[folder.name]}` : '';
    return `├── ${folder.name}/ ${comment}`;
  });

const files = items
  .filter((item) => item.isFile())
  .map((file) => {
    const comment = comments[file.name] ? `  # ${comments[file.name]}` : '';
    return `├── ${file.name} ${comment}`;
  });

const combinedStructure = [
  '```',
  '📁 루트 폴더',
  ...folders,
  '',
  '📄 루트 파일',
  ...files,
  '```'
].join('\n');

const readme = fs.readFileSync(README_PATH, 'utf-8');
const updated = readme.replace(
  /<!-- STRUCTURE-START -->([\s\S]*?)<!-- STRUCTURE-END -->/,
  `<!-- STRUCTURE-START -->\n${combinedStructure}\n<!-- STRUCTURE-END -->`
);

fs.writeFileSync(README_PATH, updated);
console.log('✅ README.md 구조 자동 업데이트 완료!');