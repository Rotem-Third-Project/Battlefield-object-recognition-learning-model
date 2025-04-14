import fs from 'fs';
import path from 'path';

const COMMENTS_PATH = path.join('.github', 'config', 'folder-comments.json');
const README_PATH = 'README.md';

// 주석 불러오기 (예외 처리 포함)
let comments: Record<string, string> = {};
try {
  comments = JSON.parse(fs.readFileSync(COMMENTS_PATH, 'utf-8'));
} catch {
  console.warn('⚠️ folder-comments.json 불러오기 실패: 주석 없이 진행합니다.');
}

// 디렉토리 항목 읽기
const items = fs.readdirSync('.', { withFileTypes: true });

// 폴더/파일 나누기
const folderItems = items.filter(
  (item) => item.isDirectory() && !item.name.startsWith('.git') && item.name !== 'node_modules'
);
const fileItems = items.filter((item) => item.isFile());

// 리스트 출력 포맷 함수
function formatItems(items: fs.Dirent[], isDirectory: boolean): string[] {
  return items.map((item, index) => {
    const isLast = index === items.length - 1;
    const symbol = isLast ? '└──' : '├──';
    const name = item.name + (isDirectory ? '/' : '');
    const comment = comments[item.name] ? `  # ${comments[item.name]}` : '';
    return `${symbol} ${name} ${comment}`;
  });
}

const folders = formatItems(folderItems, true);
const files = formatItems(fileItems, false);

// 구조 조합
const combinedStructure = [
  '```',
  '📁 루트 폴더',
  ...folders,
  '',
  '📄 루트 파일',
  ...files,
  '```'
].join('\n');

// README.md에 반영
const readme = fs.readFileSync(README_PATH, 'utf-8');
const updated = readme.replace(
  /<!-- STRUCTURE-START -->([\s\S]*?)<!-- STRUCTURE-END -->/,
  `<!-- STRUCTURE-START -->\n${combinedStructure}\n<!-- STRUCTURE-END -->`
);

fs.writeFileSync(README_PATH, updated);
console.log('✅ README.md 구조 자동 업데이트 완료!');
