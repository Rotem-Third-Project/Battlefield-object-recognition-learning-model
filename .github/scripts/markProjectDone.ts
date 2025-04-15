// 📁 .github/scripts/markProjectDone.ts

import { LinearClient } from "@linear/sdk";

const accessToken = process.env.LINEAR_ACCESS_TOKEN;
const branchName = process.env.BRANCH_NAME;

if (!accessToken || !branchName) {
  console.error("❌ 환경변수 누락 (LINEAR_ACCESS_TOKEN 또는 BRANCH_NAME)");
  process.exit(1);
}

const client = new LinearClient({ accessToken });

async function run() {
  console.log(`🧹 '${branchName}' 프로젝트를 Done으로 처리 중...`);

  const projects = await client.projects();
  const project = projects.nodes.find((p) => p.name === branchName);

  if (!project) {
    console.log("⚠️ 일치하는 프로젝트가 없어 종료합니다.");
    return;
  }

  const states = await client.projectStates();
  const doneState = states.nodes.find((s) => s.name.toLowerCase() === "done");

  if (!doneState) {
    throw new Error("❌ 'Done' 상태를 찾을 수 없습니다.");
  }

  const res = await client.client.request(
    `
    mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
      projectUpdate(id: $id, input: $input) {
        success
      }
    }
    `,
    {
      id: project.id,
      input: {
        stateId: doneState.id,
      },
    }
  );

  if (res.projectUpdate.success) {
    console.log("✅ 프로젝트 상태가 Done으로 변경되었습니다.");
  } else {
    console.log("❌ 상태 변경 실패");
  }
}

run().catch((err) => {
  console.error("❌ 실행 중 오류 발생:", err);
  process.exit(1);
});
