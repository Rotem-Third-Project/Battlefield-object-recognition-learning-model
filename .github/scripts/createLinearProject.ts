// 📁 .github/scripts/createLinearProject.ts

import { LinearClient } from "@linear/sdk";

const accessToken = process.env.LINEAR_ACCESS_TOKEN;
const branchName = process.env.BRANCH_NAME;

if (!accessToken || !branchName) {
  console.error("❌ 환경변수 LINEAR_ACCESS_TOKEN 또는 BRANCH_NAME가 없습니다.");
  process.exit(1);
}

const client = new LinearClient({ accessToken });

async function run() {
  console.log(`📦 '${branchName}' 이름으로 Linear 프로젝트 생성 중...`);

  const me = await client.viewer;
  const teams = await client.teams();
  const team = teams.nodes.find((t) => t.name === "Hyundairotem_ai2");

  if (!team) {
    throw new Error("❌ Linear 팀 'Hyundairotem_ai2'을 찾을 수 없습니다.");
  }

  const result = await client.client.request(
    `
    mutation CreateProject($input: ProjectCreateInput!) {
      projectCreate(input: $input) {
        success
        project {
          name
          id
        }
      }
    }
    `,
    {
      input: {
        name: branchName,
        teamId: team.id,
        state: "started",
      },
    }
  );

  console.log(`✅ 프로젝트 생성 완료: ${result.projectCreate.project.name}`);
}

run().catch((err) => {
  console.error("❌ 프로젝트 생성 중 오류:", err);
  process.exit(1);
});
