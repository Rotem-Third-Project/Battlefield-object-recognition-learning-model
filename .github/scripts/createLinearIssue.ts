// 📌 .github/scripts/createLinearIssue.ts

import { LinearClient } from "@linear/sdk";
import { execSync } from "child_process";
import { extractIssueData } from "./extractIssueData";

const accessToken = process.env.LINEAR_ACCESS_TOKEN;
const branchName = process.env.GITHUB_REF_NAME || "";

if (!accessToken) {
  console.error("❌ Linear Access Token이 설정되지 않았습니다.");
  process.exit(1);
}

const linear = new LinearClient({ accessToken });

async function main() {
  // 📥 커밋 메시지 수집
  const titleRaw = execSync("git log -1 --pretty=%s").toString().trim();
  const description = execSync("git log -1 --pretty=%b").toString().trim();

  // 🔍 메시지에서 키워드 및 내용 추출
  const { key, message } = extractIssueData(titleRaw);
  if (!key) {
    console.log("ℹ️ 키워드가 없어 작업을 건너뜁니다.");
    return;
  }

  const isMain = branchName === "main";
  const battlefieldProjectName = "Battlefield-object-recognition-learning-model";

  // 🔎 팀 및 프로젝트 조회
  const teams = await linear.teams();
  const team = teams.nodes.find(t => t.name === "Hyundairotem_ai2");
  if (!team) throw new Error("❌ Linear 팀을 찾을 수 없습니다.");

  const allProjects = await linear.projects();
  let project = allProjects.nodes.find(p => {
    return isMain
      ? p.name === battlefieldProjectName
      : p.name === branchName;
  });

  if (!project) {
    console.error(`❌ '${isMain ? battlefieldProjectName : branchName}'에 해당하는 프로젝트를 찾을 수 없습니다.`);
    return;
  }

  const state = (await linear.workflowStates({ filter: { team: { id: { eq: team.id } } } }))
    .nodes.find(s => s.name.toLowerCase() === "in progress");
  if (!state) throw new Error("❌ 'In Progress' 상태를 찾을 수 없습니다.");

  // 💬 HYU-12-m → 댓글 등록
  if (/^HYU-\d+-m$/.test(key)) {
    const issueKey = key.replace(/-m$/, "");
    const issue = await findIssueByKey(issueKey);
    if (!issue) {
      console.error(`⚠️ ${issueKey} 이슈를 찾을 수 없습니다.`);
      return;
    }

    await linear.client.request(
      `mutation($input: CommentCreateInput!) {
        commentCreate(input: $input) { success }
      }`,
      {
        input: {
          issueId: issue.id,
          body: message,
        },
      }
    );
    console.log(`💬 ${issueKey}에 댓글이 추가되었습니다.`);
    return;
  }

  // 🧩 HYU-12 → 서브이슈 생성
  if (/^HYU-\d+$/.test(key)) {
    const issue = await findIssueByKey(key);
    if (!issue) {
      console.error(`⚠️ ${key} 이슈를 찾을 수 없습니다.`);
      return;
    }

    const sub = await createIssue({
      teamId: team.id,
      title: message,
      parentId: issue.id,
      projectId: project.id,
      labelIds: await findLabelIds(["improvement"]),
      stateId: state.id,
    });
    console.log(`🧩 ${key} 하위 이슈 생성됨 → ${sub}`);
    return;
  }

  // 📌 HYU → 일반 이슈 생성
  if (/^HYU$/.test(key)) {
    const issueId = await createIssue({
      teamId: team.id,
      title: message,
      projectId: project.id,
      labelIds: await findLabelIds(["feature"]),
      stateId: state.id,
    });
    console.log(`✅ 일반 이슈 생성됨 → ${issueId}`);
    return;
  }

  console.log("⚠️ 키워드 형식이 인식되지 않음.");
}

// 🔎 키워드로 이슈 검색
async function findIssueByKey(identifier: string) {
  const res = await linear.client.request(
    `query ($term: String!) {
      searchIssues(term: $term) {
        nodes { id identifier }
      }
    }`,
    { term: identifier }
  );
  return res.searchIssues.nodes.find((n: any) => n.identifier === identifier);
}

// 🧠 이슈 생성 뮤테이션 공통 함수
async function createIssue(input: any) {
  const res = await linear.client.request(
    `mutation($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        issue { identifier }
      }
    }`,
    { input }
  );
  return res.issueCreate.issue.identifier;
}

// 🏷️ 라벨 이름 → ID 변환
async function findLabelIds(labelNames: string[]) {
  const labels = await linear.issueLabels();
  return labels.nodes
    .filter(l => labelNames.includes(l.name))
    .map(l => l.id);
}

main().catch(err => {
  console.error("❌ 오류:", err);
  process.exit(1);
});
