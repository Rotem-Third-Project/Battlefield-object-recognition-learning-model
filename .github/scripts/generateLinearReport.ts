// 📄 .github/scripts/generateLinearReport.ts

import { LinearClient } from "@linear/sdk";
import * as fs from "fs";

const accessToken = process.env.LINEAR_ACCESS_TOKEN;
const roadmapName = process.argv[2];
if (!accessToken || !roadmapName) {
  console.error(
    "❌ 환경변수가 누락되었거나 로드맵 이름이 입력되지 않았습니다."
  );
  process.exit(1);
}

const client = new LinearClient({ accessToken });
const outputPath = `linear-report.md`;
const lines: string[] = [];

function push(line = "") {
  lines.push(line);
}

async function main() {
  // 🔍 로드맵 조회
  const roadmaps = await client.roadmaps();
  const roadmap = roadmaps.nodes.find((r) => r.name === roadmapName);
  if (!roadmap)
    throw new Error(`❌ '${roadmapName}' 로드맵을 찾을 수 없습니다.`);

  push(`# 🧭 로드맵: ${roadmap.name}\n`);

  // 📂 로드맵에 속한 프로젝트 조회
  const roadmapProjects = await client.client.request(
    `query($id: String!) {
      roadmap(id: $id) {
        projects {
          nodes { id name completedAt startedAt state }
        }
      }
    }`,
    { id: roadmap.id }
  );

  for (const project of roadmapProjects.roadmap.projects.nodes) {
    push(`## 📂 프로젝트: ${project.name}`);
    push(`- 상태: ${project.state}`);
    push(`- 시작일: ${project.startedAt || "(미정)"}`);
    push(`- 완료일: ${project.completedAt || "(미정)"}`);

    // 해당 프로젝트의 이슈 조회
    const res = await client.client.request(
      `query($id: String!) {
        project(id: $id) {
          issues {
            nodes {
              id
              identifier
              title
              state { name }
              assignee { name }
              comments { nodes { body createdAt } }
              children { nodes { identifier title state { name } } }
            }
          }
        }
      }`,
      { id: project.id }
    );

    const issues = res.project.issues.nodes;
    for (const issue of issues) {
      push(`\n### ✅ 이슈: ${issue.identifier} | ${issue.title}`);
      push(`- 상태: ${issue.state.name}`);
      push(`- 담당자: ${issue.assignee?.name || "없음"}`);

      // 📌 코멘트 최대 3개
      const comments = issue.comments.nodes.slice(0, 3);
      if (comments.length > 0) {
        push("- 코멘트:");
        comments.forEach((c) => {
          const date = new Date(c.createdAt).toLocaleDateString("ko-KR");
          push(`  - [${date}] 🔹 ${c.body}`);
        });
      }

      // 🧩 서브이슈
      if (issue.children.nodes.length > 0) {
        issue.children.nodes.forEach((sub) => {
          push(`\n#### 🧩 서브이슈: ${sub.identifier} | ${sub.title}`);
          push(`- 상태: ${sub.state.name}`);
        });
      }

      // 🕓 타임라인 3개
      const timeline = await client.client.request(
        `query($id: String!) {
          issue(id: $id) {
            timelineEntries(first: 10) {
              nodes {
                __typename
                createdAt
                ... on Comment {
                  body
                  user { name }
                }
                ... on IssueStateChangedPayload {
                  fromState { name }
                  toState { name }
                }
                ... on IssueAssignmentPayload {
                  assignee { name }
                }
              }
            }
          }
        }`,
        { id: issue.id }
      );

      const recent = timeline.issue.timelineEntries.nodes.slice(0, 3);
      push("\n### 🕓 최근 타임라인 (최대 3개)");
      for (const entry of recent) {
        const date = new Date(entry.createdAt).toLocaleDateString("ko-KR");
        switch (entry.__typename) {
          case "Comment":
            push(`1. [${date}] 💬 ${entry.user.name}: ${entry.body}`);
            break;
          case "IssueAssignmentPayload":
            push(`1. [${date}] 👤 담당자 지정: ${entry.assignee?.name}`);
            break;
          case "IssueStateChangedPayload":
            push(
              `1. [${date}] 🔄 상태 변경: ${entry.fromState.name} → ${entry.toState.name}`
            );
            break;
          default:
            push(`1. [${date}] 📌 기타 이벤트`);
        }
      }
      push();
    }
  }

  // 💾 파일 저장
  fs.writeFileSync(outputPath, lines.join("\n"), "utf-8");
  console.log(`✅ 리포트 생성 완료 → ${outputPath}`);
}

main().catch((e) => {
  console.error("❌ 오류 발생:", e);
  process.exit(1);
});
