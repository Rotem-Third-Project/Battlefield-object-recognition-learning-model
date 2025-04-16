// 📄 .github/scripts/generateLinearReport.ts

import { LinearClient } from "@linear/sdk";
import * as fs from "fs";

const accessToken = process.env.LINEAR_ACCESS_TOKEN;
if (!accessToken) {
  console.error("❌ LINEAR_ACCESS_TOKEN 누락");
  process.exit(1);
}

const client = new LinearClient({ accessToken });
const outputPath = `linear-report.md`;
const lines: string[] = [];

function push(line = "") {
  lines.push(line);
}

async function main() {
  const allProjects = await client.projects();

  push("```mermaid");
  push("gantt");
  push("    title 프로젝트 일정");
  push("    dateFormat  YYYY-MM-DD");

  for (const project of allProjects.nodes) {
    const team = project.team?.name || "(팀 정보 없음)";
    const start = project.startedAt ? project.startedAt.slice(0, 10) : null;
    const end = project.completedAt
      ? project.completedAt.slice(0, 10)
      : project.targetDate?.slice(0, 10);

    if (!start || !end) continue; // 시작일 또는 종료일 없으면 건너뜀

    const sectionName =
      project.name.length > 30
        ? project.name.slice(0, 30) + "..."
        : project.name;
    push(`    section ${sectionName}`);
    push(`    ${team} | ${project.state} : ${project.id}, ${start}, ${end}`);
  }

  push("```\n");

  // 💾 파일 저장
  fs.writeFileSync(outputPath, lines.join("\n"), "utf-8");
  console.log(`✅ 머메이드 Gantt 리포트 생성 완료 → ${outputPath}`);
}

main().catch((e) => {
  console.error("❌ 오류 발생:", e);
  process.exit(1);
});
